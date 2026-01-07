from services.pdf import extract_text_from_pdf
from services.docx_parser import extract_text_from_docx
from services.llm import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import json
import time
import random

class ResumeData(BaseModel):
    Name: str = Field(description="Full name of the candidate")
    Contact: str = Field(description="Email and/or Phone number")
    Qualification: str = Field(description="Highest degree or qualification")
    Current_Position: str = Field(description="Current job title and company")
    Experience: str = Field(description="Total years of experience or summary of experience")
    Skills: str = Field(description="Comma separated list of top technical and professional skills")
    Top_Projects: str = Field(description="Brief summary of 1-2 top projects mentioned")

def parse_resume(file_content: bytes, filename: str) -> dict:
    # 1. Extract Text
    # For now assume PDF. If DOCX, we need another handler (e.g. python-docx).
    # Simple check:
    text = ""
    if filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_content)
    elif filename.lower().endswith(".docx"):
        text = extract_text_from_docx(file_content)
    else:
        # Fallback or error. For text files:
        try:
            text = file_content.decode('utf-8')
        except:
            return {"error": "Unsupported file format"}

    if not text:
        return {"error": "No text extracted"}

    if not text:
        print(f"DEBUG: {filename} - No text extracted.")
        return {"error": "No text extracted"}

    # Clean text (remove excessive whitespace)
    import re
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"DEBUG: {filename} - Extracted {len(text)} chars. Snippet: {text[:100]}...")
    
    if len(text) < 10:
        print(f"DEBUG: {filename} - Text too short/empty. Skipping LLM.")
        return {"error": "Insufficient text content"}

    # 2. LLM Extraction
    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=ResumeData)
    
    prompt = PromptTemplate(
        template="""
        You are an expert Resume Parser. Extract the following information from the resume text provided below.
        Return ONLY a raw JSON object. Do not include markdown formatting (like ```json).
        If a field is not found, use empty string "".
        
        Resume Content:
        {text}
        
        {format_instructions}
        """,
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser

    max_retries = 5
    base_delay = 62 # Seconds (> 60s to clear RPM limit)
    
    for attempt in range(max_retries):
        try:
            # Gemini 1.5 Flash / 2.0 Flash handles large context easily.
            # No need for truncation logic or model fallback complexity.
            result = chain.invoke({"text": text}) # Removed truncation
            print(f"DEBUG: {filename} - LLM Success: {result.get('Name')}")
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    sleep_time = base_delay + (attempt * 5) + random.uniform(0, 5)
                    print(f"⚠️ Rate Limit (429) for {filename}. Sleeping {sleep_time:.1f}s before retry {attempt+1}/{max_retries}...")
                    time.sleep(sleep_time)
                    continue
                else:
                    print(f"❌ Failed after {max_retries} retries: {filename}")
                    return {"error": "Rate Limit Exceeded"}
            else:
                # Non-retryable error
                print(f"DEBUG: {filename} - LLM Parse Error: {e}")
                return {"error": f"LLM Parse Error: {str(e)}"}

from typing import List, Tuple

class ResumeList(BaseModel):
    resumes: List[ResumeData] = Field(description="List of extracted resume data")

def parse_resumes_batch(batch_data: List[Tuple[str, str]]) -> List[dict]:
    """
    Parses a batch of resumes in one LLM call.
    batch_data: List of (filename, text_content)
    """
    import sys
    print(f"🚨 ENTERED parse_resumes_batch with {len(batch_data) if batch_data else 0} items")
    sys.stdout.flush()
    
    if not batch_data:
        print("⚠️ Empty batch_data, returning empty list")
        return []

    print(f"DEBUG: Processing Batch of {len(batch_data)} resumes...")
    sys.stdout.flush()
    
    # Construct Giant Prompt
    combined_text = ""
    for idx, (fname, text) in enumerate(batch_data):
        # Truncate to ~40k chars per resume to fit 1M window comfortably even with 20 files
        safe_text = text[:40000] 
        combined_text += f"\n--- RESUME #{idx+1} (Filename: {fname}) ---\n{safe_text}\n"

    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=ResumeList)
    
    prompt = PromptTemplate(
        template="""
        You are an expert Resume Parser. You are provided with a batch of {count} resumes text below.
        Extract the information for EACH resume and return a JSON object containing a list of resumes.
        Ensure the order matches the input order precisely.
        
        Resume Batch Content:
        {text}
        
        {format_instructions}
        """,
        input_variables=["text", "count"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    max_retries = 5
    base_delay = 62 
    
    for attempt in range(max_retries):
        try:
            # Re-Get LLM on every attempt to allow Key Switching
            llm = get_llm()
            # Add timeout to prevent hanging on slow API responses
            llm.request_timeout = 120  # 2 minutes max per batch
            chain = prompt | llm | parser

            print(f"⏱️ Calling LLM API (attempt {attempt + 1}/{max_retries}, timeout=120s)...")
            result = chain.invoke({"text": combined_text, "count": len(batch_data)})
            # Result should be {"resumes": [...]}
            data_list = result.get("resumes", [])
            print(f"DEBUG: Batch Success! Extracted {len(data_list)} items.")
            return data_list
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "insufficient_quota" in error_str:
                if attempt < max_retries - 1:
                    sleep_time = base_delay + (attempt * 5) + random.uniform(0, 5)
                    print(f"⚠️ Batch Rate Limit (429/Quota). Sleeping {sleep_time:.1f}s and Rotating Key...")
                    time.sleep(sleep_time)
                    continue
            print(f"❌ Batch LLM Error: {e}")
            return [] # Fail batch
