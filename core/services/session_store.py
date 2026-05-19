# core/services/session_store.py

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid
from django.conf import settings

# =====================================================
# SESSIONS STORAGE DIRECTORY
# =====================================================

SESSIONS_DIR = os.path.join(settings.BASE_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# =====================================================
# IN-MEMORY SESSION REGISTRY
# =====================================================

_SESSIONS: Dict[str, "InterviewSession"] = {}


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

    session = InterviewSession(
        session_id=str(uuid.uuid4()),
        company=company,
        role_label=role_label,
        designation=designation,
    )

    # ✅ STORE SESSION
    _SESSIONS[session.session_id] = session
    
    # Save to disk initially
    save_session(session)

    return session


# =====================================================
# SERIALIZER & DESERIALIZER
# =====================================================

def save_session(session: InterviewSession):
    if not session:
        return

    data = {
        "session_id": session.session_id,
        "company": session.company,
        "role_label": session.role_label,
        "designation": session.designation,
        "phase": getattr(session, "phase", "intro"),
        "finished": getattr(session, "finished", False),
        "candidate_name": getattr(session, "candidate_name", None),
        "last_answer": getattr(session, "last_answer", None),
        "answers": getattr(session, "answers", {}),
        "topics_asked": getattr(session, "topics_asked", []),
        "current_topic": getattr(session, "current_topic", None),
        "awaiting_experience": getattr(session, "awaiting_experience", False),
        "llm_hr_count": getattr(session, "llm_hr_count", 0),
        "hr_limit": getattr(session, "hr_limit", None),
        "total_questions_asked": getattr(session, "total_questions_asked", 0),
        "total_limit": getattr(session, "total_limit", None),
        "last_question": getattr(session, "last_question", None),
        "final_hr_queue": getattr(session, "final_hr_queue", None),
    }

    # Handle set serialization safely
    asked_llm_questions = getattr(session, "asked_llm_questions", set())
    data["asked_llm_questions"] = list(asked_llm_questions)

    filepath = os.path.join(SESSIONS_DIR, f"{session.session_id}.json")
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving session {session.session_id} to file: {e}")

    # Update in-memory registry cache as well
    _SESSIONS[session.session_id] = session


# =====================================================
# ACCESSOR (CRITICAL)
# =====================================================

def get_session(session_id: str) -> Optional[InterviewSession]:
    # 1. Try to fetch from in-memory dictionary
    session = _SESSIONS.get(session_id)
    if session:
        return session

    # 2. Fallback to loading from disk JSON
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            session = InterviewSession(
                session_id=data["session_id"],
                company=data["company"],
                role_label=data["role_label"],
                designation=data["designation"],
                phase=data.get("phase", "intro"),
                finished=data.get("finished", False),
                candidate_name=data.get("candidate_name"),
                last_answer=data.get("last_answer"),
                answers=data.get("answers", {}),
                topics_asked=data.get("topics_asked", []),
                current_topic=data.get("current_topic"),
                awaiting_experience=data.get("awaiting_experience", False),
                llm_hr_count=data.get("llm_hr_count", 0),
                hr_limit=data.get("hr_limit"),
            )

            # Re-hydrate non-dataclass dynamic attributes
            session.total_questions_asked = data.get("total_questions_asked", 0)
            session.total_limit = data.get("total_limit")
            session.asked_llm_questions = set(data.get("asked_llm_questions", []))
            session.last_question = data.get("last_question")
            session.final_hr_queue = data.get("final_hr_queue")

            # Store back in in-memory registry
            _SESSIONS[session_id] = session
            return session
        except Exception as e:
            print(f"Error loading session {session_id} from file: {e}")

    return None