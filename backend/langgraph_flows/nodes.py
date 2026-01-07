import json
import os
import re
from langgraph_flows.state import HRPipelineState
from services.llm import get_llm
from services.sheets import read_sheet, write_to_sheet, append_to_sheet
from services.gmail import send_email
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from typing import Dict, Any

# Prompts
JD_PROMPT = """You are an expert HR Recruiter. Extract requirements from the Job Description below.
Return ONLY a valid JSON object. Do NOT include any markdown formatting, python code, or explanations. 

Job Description:
{jd_text}

Output JSON with specific keys: job_title (str), required_skills (list), tools_tech (list), min_experience (str), responsibilities (list), must_have (list), good_to_have (list).
"""

CV_ANALYSIS_PROMPT = """You are a Strict Technical Hiring Manager. Your goal is to Identify the TOP 1% of talent and Reject the rest.
Compare the Candidate Resume against the Job Description Requirements with EXTREME scrutiny.

CRITICAL SCORING RULES:
1. Be SKEPTICAL. Assume claims are exaggerated unless supported by specific metrics, dates, or project details.
2. KEYWORD STUFFING: Do NOT give points for simply listing a skill. The candidate must demonstrate *how* they used it in their experience.
3. EXPERIENCE MATCH: Verify the *years of experience* strictly. If they lack the required years, the score MUST be below 60.
4. SCORING SCALE:
   - 90-100: Exceptional match. Has ALL skills + Deep Deep Experience + Industry Leadership.
   - 80-89: Great match. Meets ALL critical requirements with strong proof. (This is the PASS threshold).
   - 60-79: Good candidate but missing some specific requirements or depth.
   - <60: Mismatch or Unqualified.

Job Requirements: {jd_requirements}

Resume:
{resume_text}

Return ONLY a valid JSON object. Do NOT include any markdown formatting, python code, or explanations.
Output JSON with these exact keys:
match_score (0-100 int),
strengths (list of strings - be specific),
weaknesses (list of strings - be critical),
experience_validation (string comments - verify years and relevance),
skill_match_percentage (string or int - ratio of matched critical skills),
verdict ("PASS" or "FAIL" - Strict adherence to the 80/100 threshold)
"""

HR_QUESTIONS_PROMPT = """Generate personalized interview questions for this candidate.
Return ONLY a valid JSON object. Do NOT include any markdown formatting, python code, or explanations.

Candidate: {candidate_name}
Role: {job_applied_for}
Analysis: {analysis_result}

Output JSON with keys:
candidate_summary (str),
key_insights (list),
recommended_questions (list of 6-10 strings)
"""

# Nodes

def extract_jd_requirements_node(state: HRPipelineState) -> HRPipelineState:
    print("--- Extracting JD Requirements ---")
    jd_text = state.get("jd_text")
    if not jd_text:
        return {"jd_requirements": None}
    
    llm = get_llm()
    parser = JsonOutputParser()
    chain = PromptTemplate(template=JD_PROMPT, input_variables=["jd_text"]) | llm | parser
    
    requirements = chain.invoke({"jd_text": jd_text})
    
    # Save to ActiveJobSheet in STRUCTURED format compatible typically with get_all_job_descriptions
    # Format: [Job Title, Description, Required Skills, Top Projects Reference, Timestamp]
    from datetime import datetime
    
    # Process fields
    job_title = requirements.get("job_title", "Unknown Role")
    
    # Description = Responsibilities list joined
    description = "\n".join(requirements.get("responsibilities", []))
    
    # Skills = Required Skills joined
    skills = ", ".join(requirements.get("required_skills", []))
    
    # Projects = Must Have + Good to Have joined (as proxy for projects/experience context)
    projects_context = "MUST HAVE: " + ", ".join(requirements.get("must_have", []))
    
    timestamp = datetime.now().isoformat()
    
    row = [job_title, description, skills, projects_context, timestamp]
    
    append_to_sheet("ActiveJobSheet!A:E", [row])
    
    return {"jd_requirements": requirements}

def fetch_new_candidates_node(state: HRPipelineState) -> HRPipelineState:
    # This node might be triggered to find *one* candidate to process if passed in input,
    # or find list. Assuming single candidate pipeline for now as per "trigger-candidate-sync"
    # If state has 'candidate_data', we skip fetching
    if state.get("candidate_data"):
        return {} # Already have data
    
    # Logic to find new candidates would normally return a LIST.
    # But graph state is singular in our design. 
    # See graph.py for how we handle iteration.
    return {}





def analyze_cv_node(state: HRPipelineState) -> HRPipelineState:
    # Validations
    fail_reason = None
    if not state.get("resume_text"):
        fail_reason = "No resume text"
    
    jd_reqs = state.get("jd_requirements")
    if not fail_reason and not jd_reqs:
        fail_reason = "No JD context (ActiveJobSheet empty?)"

    from datetime import datetime
    name = state["candidate_data"].get("Name", "Unknown")
    job = state["candidate_data"].get("Job Applied For", "Unknown")

    analysis_sheet_name = f"Analysis - {job}"
    
    # Validation Headers
    ANALYSIS_HEADERS = [
        "Candidate Name", "Match Score", "Strengths", "Weaknesses", 
        "Experience Check", "Skill Match", "Verdict", "Timestamp", 
        "Job Applied For", "Email", "Contact"
    ]

    contact_info = state["candidate_data"].get("Contact", "")
    email = state["candidate_data"].get("Email", "")
    
    # If explicit email is missing, extract from contact
    if not email:
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_info)
        email = email_match.group(0) if email_match else ""
        
    # CLEANUP: Remove email from contact_info to avoid duplication and mess
    if email and email in contact_info:
        # Remove email
        cleaned_contact = contact_info.replace(email, "").strip()
        # Clean up commas/unnecessary chars left over
        cleaned_contact = re.sub(r'^[,;\s]+|[,;\s]+$', '', cleaned_contact)
        contact_info = cleaned_contact
        
    # ESCAPE: Prepend ' if starts with + or = (Google Sheets Formula Injection)
    if contact_info and (contact_info.startswith("+") or contact_info.startswith("=")):
        contact_info = "'" + contact_info

    if fail_reason:
        # Write failure to sheet immediately
        print(f"❌ CV Analysis Failed: {fail_reason}")
        row = [name, 0, "", "", fail_reason, "0%", "FAIL", datetime.now().isoformat(), job, email, contact_info]
        
        # Ensure sheet exists first
        from services.sheets import ensure_sheet_exists
        ensure_sheet_exists(analysis_sheet_name, ANALYSIS_HEADERS)
        
        append_to_sheet(f"{analysis_sheet_name}!A:K", [row])
        return {"verdict": "FAIL", "analysis_result": {"reason": fail_reason}}
    
    llm = get_llm()
    parser = JsonOutputParser()
    chain = PromptTemplate(template=CV_ANALYSIS_PROMPT, input_variables=["jd_requirements", "resume_text"]) | llm | parser
    
    # Adapt JD Context: If it's a dict with our new keys, format it nicely.
    jd_context_str = ""
    if isinstance(jd_reqs, dict) and "description" in jd_reqs:
        jd_context_str = f"""
        Job Description: {jd_reqs.get('description', '')}
        
        CRITICAL Required Skills: {jd_reqs.get('skills', '')}
        
        CRITICAL Reference Projects: {jd_reqs.get('top_projects', '')}
        """
    else:
        # Fallback for old style or raw JSON
        jd_context_str = json.dumps(jd_reqs)

    analysis = chain.invoke({"jd_requirements": jd_context_str, "resume_text": state["resume_text"]})
    
    # Enforce Score Threshold
    raw_score = str(analysis.get("match_score", "0")).replace("%", "").strip()
    try:
        score_int = int(raw_score)
    except:
        score_int = 0
        
    if score_int >= 80:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    
    # Update analysis object with enforced verdict so it propagates potentially
    analysis["verdict"] = verdict
    
    # Save to Job-Specific Analysis Sheet
    
    row = [
        name,
        analysis.get("match_score"),
        ", ".join(analysis.get("strengths", [])),
        ", ".join(analysis.get("weaknesses", [])),
        analysis.get("experience_validation"),
        str(analysis.get("skill_match_percentage")),
        verdict,
        datetime.now().isoformat(),
        job,
        email,
        contact_info
    ]
    
    from services.sheets import ensure_sheet_exists
    ensure_sheet_exists(analysis_sheet_name, ANALYSIS_HEADERS)
    append_to_sheet(f"{analysis_sheet_name}!A:K", [row])
    
    return {"analysis_result": analysis, "verdict": verdict}


def generate_hr_questions_node(state: HRPipelineState) -> HRPipelineState:
    print("--- Generating HR Questions ---")
    candidate_name = state["candidate_data"].get("Name")
    job = state["candidate_data"].get("Job Applied For")
    analysis = state.get("analysis_result")
    
    llm = get_llm()
    parser = JsonOutputParser()
    chain = PromptTemplate(template=HR_QUESTIONS_PROMPT, input_variables=["candidate_name", "job_applied_for", "analysis_result"]) | llm | parser
    
    questions_data = chain.invoke({
        "candidate_name": candidate_name, 
        "job_applied_for": job, 
        "analysis_result": json.dumps(analysis)
    })
    
    # Save to HRQuestions Sheet
    # Columns: Date, Candidate Name, Job, Questions, Resume Link
    from datetime import datetime
    questions_list = "\n".join(questions_data.get("recommended_questions", []))
    resume_link = state.get("resume_url", "N/A")
    row = [datetime.now().isoformat(), candidate_name, job, resume_link, questions_list]
    append_to_sheet("HRQuestions!A:E", [row])
    
    return {"hr_questions": questions_data}

def send_to_hr_node(state: HRPipelineState) -> HRPipelineState:
    print("--- Sending Email to HR ---")
    candidate_name = state["candidate_data"].get("Name")
    job = state["candidate_data"].get("Job Applied For")
    analysis = state.get("analysis_result")
    questions = state.get("hr_questions", {}).get("recommended_questions", [])
    
    score = analysis.get("match_score")
    summary = state.get("hr_questions", {}).get("candidate_summary", "")
    
    subject = f"Interview Questions for Candidate: {candidate_name}"
    
    q_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    
    
    # If PASS, Auto-Schedule is DISABLED (Moved to Manual UI Control)
    interview_info = ""
    if state.get("verdict") == "PASS":
        print("ℹ️ Auto-scheduling skipped. Waiting for manual trigger via UI.")
        interview_info = "\nℹ️ Interview Status: Pending Manual Invite\n"
        

    body = f"""
Candidate Name: {candidate_name}
Applied for Job: {job}
Match Score: {score}
Summary: {summary}

{interview_info}
Strengths: {", ".join(analysis.get("strengths", []))}
Weaknesses: {", ".join(analysis.get("weaknesses", []))}

AI Recommended Interview Questions:
{q_text}
"""
    # Single HR account handles everything - sends email to itself with candidate analysis
    hr_email = os.getenv("GMAIL_USER_EMAIL", "hr@obizworks.com") 
    success = send_email(hr_email, subject, body)
    
    return {"email_sent": success}
