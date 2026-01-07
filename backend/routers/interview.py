from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import shutil
import tempfile
from services.llm import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from openai import OpenAI

# Initialize Router
router = APIRouter()

# Initialize Groq Client for STT (Speech to Text)
# We use the OpenAI client compatible with Groq's API
def get_groq_audio_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("⚠️ GROQ_API_KEY not found. STT will fail.")
        return None
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

@router.post("/process")
async def process_interview_audio(
    audio: UploadFile = File(...),
    candidate_email: str = Form(...),

    job_title: str = Form(...),
    history: str = Form(default="") # Simple history string passed from frontend
):
    try:
        # 1. Save Audio Temporarily
        suffix = os.path.splitext(audio.filename)[1] or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name
        
        # 2. Transcribe (STT) via Groq
        client = get_groq_audio_client()
        if not client:
            return {"error": "Server configuration error (Missing API Key)"}
        
        # DEBUG: Check file size
        file_size = os.path.getsize(tmp_path)
        print(f"🎤 Audio File Size: {file_size} bytes")
        
        if file_size < 100:
            print("⚠️ Audio file is too small (silent/empty).")
            return {
                "transcript": "",
                "response": "I didn't catch that. It seems the audio was empty.",
                "is_success": False
            }

        with open(tmp_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(tmp_path, file.read()),
                model="whisper-large-v3",
                prompt="The candidate is speaking during a job interview. They are introducing themselves and discussing their qualifications.",
                response_format="json",
                language="en",
                temperature=0.0
            )


        
        user_text = transcription.text.strip()
        print(f"🗣️ Raw Transcription Result: '{user_text}'")
        
        # Hallucination Filter (Whisper often outputs 'you' or 'Thank you' on silence)
        hallucinations = [
            "you", "thank you", "thanks for watching", "subtitles by",
            "they are introducing themselves and discussing their qualifications",
            "the job interview is a very important part of the job interview process",
            "hello everyone", "my name is", "i am a", "hello"
        ]

        
        # Remove all punctuation for check
        import string
        cleaned_text = user_text.lower().translate(str.maketrans('', '', string.punctuation)).strip()
        
        if not user_text or len(cleaned_text) < 2 or cleaned_text in hallucinations:
            print(f"⚠️ Detected Silence/Hallucination: '{user_text}' -> Treat as empty.")
            return {
                "transcript": "",
                "response": "I couldn't hear you clearly. Could you please repeat that?",
                "is_success": False
            }


        
        # Cleanup temp file
        os.remove(tmp_path)

        # 3. Generate AI Response
        import datetime
        from services.sheets import append_to_sheet, ensure_sheet_exists, get_candidate_name_by_email, get_questions_by_name
        
        # 1. Fetch Target Questions (if available)
        target_questions = None
        candidate_name = get_candidate_name_by_email(job_title, candidate_email)
        if candidate_name:
            target_questions = get_questions_by_name(job_title, candidate_name)
            
        print(f"📋 Target Questions Found: {bool(target_questions)}")

        # --- IMMEDIATE DISQUALIFICATION CHECK ---
        if "SYSTEM: CANDIDATE DISQUALIFIED" in history:
            print("🚨 Candidate Disqualified (Cheating Detected). Forcing FAIL.")
            
            # Save FAIL to Sheet
            ensure_sheet_exists("VoiceInterviews", headers=["Date", "Candidate Email", "Job Title", "Score", "Verdict", "Feedback", "Transcript Link"])
            row = [
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                candidate_email,
                job_title,
                0,        # Score
                "FAIL",   # Verdict
                "DISQUALIFIED: Cheating detected (Tab Switching/Suspicious Activity).", # Feedback
                "See App Logs"
            ]
            append_to_sheet("VoiceInterviews!A:G", [row])
            
            return {
                "transcript": "",
                "response": "Interview Terminated.",
                "is_success": True,
                "is_terminated": True
            }
        # ----------------------------------------

        # Enhanced Prompt ensuring Agent Control
        if target_questions:
            # STRICT MODE: Ask specific questions
            INTERVIEWER_PROMPT = f"""You are an expert AI Recruiter conducting a voice interview for the role of "{{job_title}}".
            Candidate Name: {candidate_name or 'Unknown'}
            
            GOAL: You have a REQUIRED list of questions generated specifically for this candidate based on their resume.
            
            REQUIRED QUESTIONS LIST:
            {target_questions}
            
            INSTRUCTIONS:
            1. Compare the 'Current Conversation History' with the 'REQUIRED QUESTIONS LIST'.
            2. Identify which questions have ALREADY been asked.
            3. Select the NEXT specific question from the list.
            4. Ask ONE question at a time.
            5. If the candidate answers poorly, you may ask ONE brief follow-up, but then return to the list immediately.
            6. CRITICAL: You MUST ask ALL questions from the list.
            
            TERMINATION:
            - ONLY after the candidate has answered ALL questions in the list, then say:
            "Thank you for your time. We will be in touch. <END_INTERVIEW>"
            
            Current Conversation History:
            {{history}}
            
            Candidate just said: "{{user_input}}"
            
            Response Guidelines:
            - Be professional but friendly.
            - Keep spoken responses short.
            - No markdown.
            """
        else:
            # FALLBACK MODE (Generic)
            INTERVIEWER_PROMPT = """You are an expert AI Recruiter conducting a voice interview for the role of "{job_title}".
            
            GOAL: Assess the candidate's core skills in a concise manner (approx 3 questions).
            
            STRUCTURE:
            1. If this is the start (history is empty), introduce yourself and ask them to introduce themselves.
            2. Ask 2-3 relevant technical/behavioral questions based on the role.
            3. ONE QUESTION AT A TIME. Wait for their answer.
            4. Once you have asked 3 questions and received answers, OR if the candidate is clearly not a fit, ends the interview.
            
            TERMINATION:
            When you decide to end the interview, you MUST say:
            "Thank you for your time. We will be in touch. <END_INTERVIEW>"
            (Do not say <END_INTERVIEW> unless you are 100% finished).
            
            Current Conversation History:
            {history}
            
            Candidate just said: "{user_input}"
            
            Response Guidelines:
            - Be professional but friendly.
            - Keep spoken responses short (2-4 sentences).
            - No markdown.
            """
        
        llm = get_llm()
        chain = PromptTemplate(template=INTERVIEWER_PROMPT, input_variables=["job_title", "history", "user_input"]) | llm | StrOutputParser()
        
        ai_response = chain.invoke({
            "job_title": job_title,
            "history": history,
            "user_input": user_text
        })
        
        # Check for Termination Token OR Standard Phrases (Fallback)
        is_terminated = "<END_INTERVIEW>" in ai_response
        clean_response = ai_response.replace("<END_INTERVIEW>", "").strip()
        
        # Robust Fallback: If agent said goodbye but forgot token
        termination_phrases = ["thank you for your time", "we will be in touch", "end of the interview"]
        if not is_terminated:
            for phrase in termination_phrases:
                if phrase.lower() in clean_response.lower():
                    is_terminated = True
                    print(f"⚠️ Termination Phrase Detected: '{phrase}'. Forcing Termination.")
                    break
        
        print(f"🤖 Agent Response: {clean_response} (Terminated: {is_terminated})")
        
        # 4. Grading & Persistence (If Terminated)
        grading_data = {}
        if is_terminated:
            print("📝 Interview Finished. Grading Candidate...")
            try:
                # 4a. Grade the specific interview session
                GRADING_PROMPT = """You are a Senior Hiring Manager. Grade this interview transcript for a {job_title} role.
                
                Transcript:
                {history}
                Candidate: {user_input}
                
                Return JSON ONLY:
                {{
                    "score": "0-10",
                    "verdict": "PASS or FAIL",
                    "feedback": "1 short sentence summary"
                }}
                """
                
                grade_chain = PromptTemplate(template=GRADING_PROMPT, input_variables=["job_title", "history", "user_input"]) | llm | StrOutputParser()
                grade_json = grade_chain.invoke({"job_title": job_title, "history": history, "user_input": user_text})
                
                # Simple parsing (robustness would rely on structured output parser, doing manual clean for now)
                import json
                try:
                    # Clean potential markdown code blocks
                    grade_str = grade_json.replace("```json", "").replace("```", "").strip()
                    grades = json.loads(grade_str)
                except:
                    grades = {"score": "N/A", "verdict": "REVIEW", "feedback": "Parsing error"}
                
                # 4b. Save to Sheets
                ensure_sheet_exists("VoiceInterviews", headers=["Date", "Candidate Email", "Job Title", "Score", "Verdict", "Feedback", "Transcript Link"])
                
                # We save a summary. Ideally we'd save full text but it's long. Saving 'history' context.
                row = [
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    candidate_email,
                    job_title,
                    grades.get("score"),
                    grades.get("verdict"),
                    grades.get("feedback"),
                    "See App Logs" # Placeholder for full transcript URL if we had blob storage
                ]
                append_to_sheet("VoiceInterviews!A:G", [row])
                print(f"✅ Saved Interview Results: {grades}")
                
            except Exception as e:
                print(f"❌ Grading/Save Error: {e}")

        return {
            "transcript": user_text,
            "response": clean_response,
            "is_success": True,
            "is_terminated": is_terminated
        }
        
    except Exception as e:
        print(f"❌ Error in voice processing: {e}")
        return {"error": str(e), "transcript": "", "response": "Sorry, I encountered an error processing your audio."}
