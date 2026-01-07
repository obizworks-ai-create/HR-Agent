from typing import TypedDict, Optional, Dict, Any, List

class HRPipelineState(TypedDict):
    jd_text: Optional[str]
    jd_requirements: Optional[Dict[str, Any]]
    
    # Candidate info
    candidate_data: Optional[Dict[str, Any]] # From sheet row
    resume_url: Optional[str]
    resume_text: Optional[str]
    
    # Analysis
    analysis_result: Optional[Dict[str, Any]] # Score, Strengths, Weaknesses
    verdict: Optional[str] # PASS / FAIL
    
    # HR Output
    hr_questions: Optional[Dict[str, Any]]
    email_sent: bool
