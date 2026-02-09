from django.shortcuts import render

# Create your views here.
# core/views.py

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.services.session_store import create_session
from core.services.role_orchestrator import get_next_question
from core.services.tts import synthesize_to_base64
from core.services import evaluator

# from core.data import master_roles
import os

# =====================================================
# IN-MEMORY SESSION STORE
# =====================================================

SESSIONS = {}   # session_id -> InterviewSession


# =====================================================
# MASTER DATA HELPERS
# =====================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

MASTER_FILE = os.path.join(
    CURRENT_DIR,
    "data",
    "master_roles.json"
)

def load_master():
    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================
# DOMAIN / ROLE APIs
# =====================================================

def list_domains(request):
    master = load_master()
    domains = [
        {
            "id": d["id"],
            "label": d["label"],
            "description": d["description"],
        }
        for d in master["domains"] if d.get("active")
    ]
    return JsonResponse({"domains": domains})


def list_roles(request, domain_id):
    master = load_master()

    for d in master["domains"]:
        if d["id"] == domain_id:
            roles = [
                {
                    "id": r["id"],
                    "label": r["label"],
                    "experience": r["experience"],
                    "education": r["education"],
                }
                for r in d["roles"] if r.get("active")
            ]
            return JsonResponse({"roles": roles})

    return JsonResponse({"error": "Domain not found"}, status=404)


# =====================================================
# INTERVIEW START
# =====================================================

@csrf_exempt
def start_interview(request):
    """
    POST:
    {
        "company": "KnowCraft",
        "role_label": "Associate HR",
        "designation": "associate_hr"
    }
    """

    data = json.loads(request.body)

    session = create_session(
        company=data["company"],
        role_label=data["role_label"],
        designation=data["designation"],
    )

    SESSIONS[session.session_id] = session

    q = get_next_question(session)

    return JsonResponse({
        "session_id": session.session_id,
        "question": q,
        "audio": synthesize_to_base64(q["text"]),
        "finished": False,
    })


# =====================================================
# ANSWER → NEXT QUESTION
# =====================================================

@csrf_exempt
def next_question(request):
    """
    POST:
    {
        "session_id": "...",
        "answer": "text answer from user"
    }
    """

    data = json.loads(request.body)
    session_id = data["session_id"]
    answer = data.get("answer", "")

    session = SESSIONS.get(session_id)

    if not session:
        return JsonResponse({"error": "Invalid session"}, status=400)

    session.last_answer = answer
    session.answers[getattr(session, "last_question", {}).get("id", "unknown")] = answer

    q = get_next_question(session)

    return JsonResponse({
        "question": q,
        "audio": synthesize_to_base64(q["text"]),
        "finished": session.finished,
    })


# =====================================================
# TTS ONLY (OPTIONAL)
# =====================================================

@csrf_exempt
def tts_only(request):
    """
    POST:
    {
        "text": "Hello"
    }
    """

    data = json.loads(request.body)
    audio = synthesize_to_base64(data["text"])

    return JsonResponse({"audio": audio})



def index(request):
    return render(request, "index.html")