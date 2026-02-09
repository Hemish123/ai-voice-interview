# core/services/session_store.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid


# =====================================================
# SESSION STATE OBJECT
# =====================================================

@dataclass
class InterviewSession:

    # -------- identity --------
    session_id: str

    company: str
    role_label: str
    designation: str

    # -------- conversation state --------
    phase: str = "intro"
    finished: bool = False

    candidate_name: Optional[str] = None

    last_answer: Optional[str] = None

    answers: Dict[str, str] = field(default_factory=dict)

    # -------- screening topic loop --------
    topics_asked: List[str] = field(default_factory=list)
    current_topic: Optional[str] = None
    awaiting_experience: bool = False

    # -------- HR block --------
    llm_hr_count: int = 0
    hr_limit: Optional[int] = None


# =====================================================
# FACTORY
# =====================================================

def create_session(company: str, role_label: str, designation: str):

    return InterviewSession(
        session_id=str(uuid.uuid4()),
        company=company,
        role_label=role_label,
        designation=designation,
    )
