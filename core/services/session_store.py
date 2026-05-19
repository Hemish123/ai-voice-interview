# core/services/session_store.py

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid
from django.conf import settings

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

    return session


# =====================================================
# SERIALIZER & DESERIALIZER
# =====================================================

def save_session(session: InterviewSession):
    if not session:
        return

    # Update in-memory registry cache
    _SESSIONS[session.session_id] = session

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

    # Save to Django database
    try:
        from core.models import InterviewSession as DBInterviewSession
        db_sess = DBInterviewSession.objects.filter(id=session.session_id).first()
        if db_sess:
            db_sess.state_json = json.dumps(data, ensure_ascii=False)
            db_sess.save()
    except Exception as e:
        print(f"Error saving session {session.session_id} to database: {e}")


# =====================================================
# ACCESSOR (CRITICAL)
# =====================================================

def get_session(session_id: str) -> Optional[InterviewSession]:
    # 1. Bypass in-memory dictionary to ensure consistency across multiple workers
    # session = _SESSIONS.get(session_id)
    # if session:
    #     return session

    # 2. Fallback to loading from database state_json
    try:
        from core.models import InterviewSession as DBInterviewSession
        db_sess = DBInterviewSession.objects.filter(id=session_id).first()
        if db_sess and db_sess.state_json:
            data = json.loads(db_sess.state_json)

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
        print(f"Error loading session {session_id} from database: {e}")

    return None