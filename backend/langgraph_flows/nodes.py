import json
import os
import re
from datetime import datetime
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

CV_ANALYSIS_PROMPT = """You are a Balanced Technical Hiring Manager. Your goal is to Identify potential talent fairly.
Compare the Candidate Resume against the Job Description Requirements with OBJECTIVE evaluation.

SCORING GUIDELINES:
1. Be FAIR but REALISTIC. Look for transferable skills and potential, not just exact keyword matches.
2. EXPERIENCE: Verify the years of experience. If they are close (e.g., 2.5 vs 3 years), do not penalize heavily if skills are strong.
3. QUALITY OVER QUANTITY: Focus on project impact and role responsibilities.
4. SCORING SCALE:
   - 90-100: Exceptional match. Exceeds requirements significantly.
   - 80-89: Strong match. Meets core requirements well. (This is the PASS threshold).
   - 70-79: Good potential. Meets most requirements but may need some upskilling.
   - <70: Mismatch or significantly underqualified.

Job Requirements: {jd_requirements}

Resume:
{resume_text}

Return ONLY a valid JSON object. Do NOT include any markdown formatting, python code, or explanations.
Output JSON with these exact keys:
match_score (0-100 int),
strengths (list of strings - highlight key assets),
weaknesses (list of strings - be constructive),
experience_validation (string comments - note years and relevance),
skill_match_percentage (string or int - ratio of matched critical skills),
verdict ("PASS" or "FAIL" - Generally PASS if score >= 80)
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
    
    # Include default "Active" status for new jobs
    row = [job_title, description, skills, projects_context, timestamp, "Active"]
    
    append_to_sheet("ActiveJobSheet!A:F", [row])
    
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






# --- GEMINI 2.5 MIGRATION START ---
from services.llm import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def analyze_with_llama(state, jd_context_str):
    print("🐴 Falling back to Llama 3.3-70b (Cerebras)...")
    try:
        llm = get_llm("llama-3.3-70b")
        prompt = CV_ANALYSIS_PROMPT.format(jd_requirements=jd_context_str, resume_text=state["resume_text"])
        
        # Ensure the prompt asks for JSON specifically if not already
        system_msg = "You are a Strict Technical Hiring Manager. Return ONLY valid JSON."
        messages = [
            ("system", system_msg),
            ("human", prompt)
        ]
        
        response = llm.invoke(messages)
        content = response.content
        
        # Parse JSON
        import json
        json_str = content.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
            
        return json.loads(json_str)
    except Exception as e:
        print(f"❌ Llama Fallback Failed: {e}")
        raise e

def analyze_cv_node(state: HRPipelineState) -> HRPipelineState:
    from datetime import datetime
    # 1. Extract Variables
    name = state["candidate_data"].get("Name", "Unknown")
    job = state["candidate_data"].get("Job Applied For", "Unknown")
    contact_info = state["candidate_data"].get("Contact", "")
    email = state["candidate_data"].get("Email", "")
    experience = state["candidate_data"].get("Experience", "")
    
    # 2. Email/Contact Cleanup (Global Hunter Fallback)
    import re
    if not email:
        # Search Contact first
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_info)
        if email_match:
            email = email_match.group(0)
        else:
            # Fallback to Experience (LLM often shifts email here)
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', experience)
            email = email_match.group(0) if email_match else ""
            
    # Clean up Email from Contact info
    if email and email.lower() in contact_info.lower():
        # Case insensitive replace
        pattern = re.compile(re.escape(email), re.IGNORECASE)
        contact_info = pattern.sub("", contact_info).strip()
        contact_info = re.sub(r'^[,;\s\|]+|[,;\s\|]+$', '', contact_info)

    # Final logic: If contact info still contains degrees/rubbish after removing email, clean it
    is_degree = any(deg in contact_info.lower() for deg in ["bba", "mba", "acca", "degree", "hons", "finance", "accounts"])
    if is_degree and len(contact_info) > 5 and "@" not in contact_info:
        # Contact column is likely a degree, not a phone number. 
        # Don't delete it completely, but mark it for cleaner display if it's identical to name
        pass

    if contact_info and (contact_info.startswith("+") or contact_info.startswith("=")):
        contact_info = "'" + contact_info

    # 3. Setup Sheet
    analysis_sheet_name = f"Analysis - {job}"
    ANALYSIS_HEADERS = [
        "Job Applied For", "Timestamp", "Email", "Phone Number", 
        "Candidate Name", "Strengths", "Weaknesses", "Experience Check", 
        "Skill Match", "Match Score", "Verdict"
    ]
    
    # --- DEDUPLICATION CHECK START ---
    # --- DEDUPLICATION CHECK START ---
    try:
        from services.sheets import ensure_sheet_exists, read_sheet
        ensure_sheet_exists(analysis_sheet_name, ANALYSIS_HEADERS)
        
        # Read existing names (Column E) to prevent duplicate analysis
        existing_rows = read_sheet(f"{analysis_sheet_name}!E:E")
        if existing_rows:
            existing_names = {r[0].strip().lower() for r in existing_rows[1:] if r} # Skip header
            if name.strip().lower() in existing_names:
                print(f"⏭️ Skipping Analysis for '{name}' - Already exists in '{analysis_sheet_name}'")
                # Return 'dummy' success state so the graph continues gracefully but doesn't write duplicates
                return {
                    "verdict": "SKIPPED", 
                    "analysis_result": {"match_score": 0, "verdict": "SKIPPED", "reason": "Duplicate"}
                }
    except Exception as e:
        print(f"⚠️ Warning: Deduplication check failed for {name}: {e}")
    # --- DEDUPLICATION CHECK END ---

    jd_reqs = state["jd_requirements"]
    
    # Context Prep
    jd_context_str = ""
    if isinstance(jd_reqs, dict) and "description" in jd_reqs:
        jd_context_str = f"""
        Job Description: {jd_reqs.get('description', '')}
        CRITICAL Required Skills: {jd_reqs.get('skills', '')}
        CRITICAL Reference Projects: {jd_reqs.get('top_projects', '')}
        """
    else:
        import json
        jd_context_str = json.dumps(jd_reqs)

    analysis = {}
    
    # CHECK FALLBACK FLAG
    if state.get("use_fallback", False):
        try:
           analysis = analyze_with_llama(state, jd_context_str)
        except Exception as e:
           # Final Fail
           pass
    else:
        # GEMINI LOGIC
        try:
            from google import genai
            from google.genai import types
            import json
            
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                 raise ValueError("GOOGLE_API_KEY for Gemini not found")
                 
            client = genai.Client(api_key=api_key)
            final_prompt = CV_ANALYSIS_PROMPT.format(jd_requirements=jd_context_str, resume_text=state["resume_text"])
            
            print("🧠 calling gemini-3-flash-preview...")
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=final_prompt,
                config={
                    "system_instruction": "You are a Strict Technical Hiring Manager.",
                    "thinking_config": types.ThinkingConfig(thinking_level="low"),
                    "temperature": 0,  # Deterministic output - same input = same output
                }
            )
            
            model_answer = ""
            if hasattr(response, "text") and response.text:
                model_answer = response.text
            elif hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content and hasattr(candidate.content, "parts") and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            model_answer += part.text
            
            if not model_answer:
                raise ValueError("Empty response from model")

            # JSON Cleaning & Parsing
            json_str = model_answer.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
                
            analysis = json.loads(json_str)
            print(f"✅ Gemini 2.5 Analysis Complete. Score: {analysis.get('match_score')}")

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str or "UNAVAILABLE" in error_str:
                 print(f"⚠️ Gemini Transient Error ({error_str[:30]}...) encountered. Propagating...")
                 raise e # Raise to api.py for retry logic
            
            print(f"⚠️ Gemini Failed ({e}). Switching to Llama 3.3 Fallback...")
            try:
                analysis = analyze_with_llama(state, jd_context_str)
            except Exception as fallback_err:
                 print(f"❌ Both Models Failed. {fallback_err}")
                 fail_reason = f"AI Analysis Error: {str(e)} | Fallback Error: {str(fallback_err)}"
                 # ... save fail logic ...
                 row = [job, datetime.now().isoformat(), email, contact_info, name, "", "", fail_reason, "0%", 0, "FAIL"]
                 return {"verdict": "FAIL", "analysis_result": {"reason": fail_reason}}

    # COMMON SUCCESS PATH
    if analysis:
        verdict = analysis.get("verdict", "FAIL").upper()
        if "PASS" in verdict: verdict = "PASS"
        else: verdict = "FAIL"
        
        # Save to Google Sheet
        strengths = analysis.get("strengths", [])
        if isinstance(strengths, list): strengths = "\n".join(strengths)
        
        weaknesses = analysis.get("weaknesses", [])
        if isinstance(weaknesses, list): weaknesses = "\n".join(weaknesses)
        
        skill_match = analysis.get("skill_match_percentage")
        if isinstance(skill_match, (int, float)):
            skill_match = f"{skill_match}%"
        elif isinstance(skill_match, str) and "%" not in skill_match:
             # If it's a string number like "25", add %
            if skill_match.isdigit():
                skill_match = f"{skill_match}%"

        # Strict A-K Mapping:
        # A=[0] Job, B=[1] Time, C=[2] Email, D=[3] Phone, E=[4] Name
        # F=[5] Strength, G=[6] Weakness, H=[7] Exp, I=[8] Skill, J=[9] Score, K=[10] Verdict
        
        # Match Score: Force TEXT format using apostrophe to prevent 8200% sheet issue
        raw_score = str(analysis.get("match_score", 0)).replace("%", "").strip()
        match_score_val = f"'{raw_score}"
        
        row = [
            job,
            datetime.now().isoformat(),
            email,
            contact_info,
            name,
            strengths,
            weaknesses,
            analysis.get("experience_validation"),
            skill_match,
            match_score_val,
            verdict
        ]
        
        from services.sheets import ensure_sheet_exists, read_sheet
        ensure_sheet_exists(analysis_sheet_name, ANALYSIS_HEADERS)
        
        # --- DOUBLE CHECK (Race Condition Safety) ---
        # Read Col A to ensure not added during processing
        try:
            current_rows = read_sheet(f"{analysis_sheet_name}!E:E")
            if current_rows:
                c_names = {r[0].strip().lower() for r in current_rows[1:] if r}
                if name.strip().lower() in c_names:
                    print(f"🛑 Double-Check: '{name}' appeared in sheet during analysis. Aborting write.")
                    return {"verdict": verdict, "analysis_result": analysis}
        except Exception as e:
            print(f"⚠️ Warning: Double-check failed: {e}")
        # --------------------------------------------
        
        print(f"DEBUG: Attempting to write to {analysis_sheet_name}!A:K")
        print(f"DEBUG: Row Data: {row}")
        
        res = append_to_sheet(f"{analysis_sheet_name}!A:K", [row])
        print(f"DEBUG: Write Result: {res}")
        
        return {
            "verdict": verdict,
            "analysis_result": analysis
        }
    
    return {"verdict": "FAIL", "analysis_result": {"reason": "Unknown Error"}}
        
    # --- GEMINI 3.0 MIGRATION END ---
    
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
    
    # Update analysis object with enforced verdict
    analysis["verdict"] = verdict
    
    # Save to Job-Specific Analysis Sheet
    row = [
        job,
        datetime.now().isoformat(),
        email,
        contact_info,
        name,
        ", ".join(analysis.get("strengths", [])),
        ", ".join(analysis.get("weaknesses", [])),
        analysis.get("experience_validation"),
        str(analysis.get("skill_match_percentage")),
        analysis.get("match_score"),
        verdict
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

    # --- DEDUPLICATION CHECK START ---
    try:
        from services.sheets import ensure_sheet_exists, read_sheet
        # Columns: Date, Candidate Name, Job, Resume Link, Questions
        ensure_sheet_exists("HRQuestions", ["Date", "Candidate Name", "Job", "Resume Link", "Questions"])
        
        # Read existing names (Column B, which is index 1)
        existing_rows_q = read_sheet("HRQuestions!B:B")
        if existing_rows_q:
            existing_names_q = {r[0].strip().lower() for r in existing_rows_q[1:] if r}
            if candidate_name and candidate_name.strip().lower() in existing_names_q:
                print(f"⏭️ Skipping HR Questions for '{candidate_name}' - Already exists in 'HRQuestions'")
                return {"hr_questions": {"recommended_questions": [], "candidate_summary": "Skipped (Duplicate)"}}
    except Exception as e:
        print(f"⚠️ Warning: HR Questions deduplication check failed: {e}")
    # --- DEDUPLICATION CHECK END ---
    
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
    # --- DOUBLE CHECK (Race Condition Safety) ---
    try:
        from services.sheets import read_sheet
        current_rows_q = read_sheet("HRQuestions!B:B")
        if current_rows_q:
            q_names = {r[0].strip().lower() for r in current_rows_q[1:] if r}
            if candidate_name and candidate_name.strip().lower() in q_names:
                print(f"🛑 Double-Check: '{candidate_name}' appeared in HR Questions during generation. Aborting write.")
                return {"hr_questions": questions_data}
    except Exception as e:
        print(f"⚠️ Warning: HR Questions Double-check failed: {e}")
    # --------------------------------------------

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
