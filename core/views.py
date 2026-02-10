# core/views.py

import os
import uuid
import json

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from core.services.auto_ingest import ingest_document
from core.services.interview_engine import get_next_question

from core.services.tts import synthesize_to_base64


# =====================================================
# CONFIG
# =====================================================

UPLOAD_DIR = os.path.join(settings.BASE_DIR, "uploads")

SESSIONS = {}   # session_id -> InterviewSession


# =====================================================
# PAGE
# =====================================================

def index(request):
    return render(request, "index.html")


# =====================================================
# START AUTO JD MODE (ONLY ENTRY)
# =====================================================

@csrf_exempt
def api_start_auto(request):

    file = request.FILES.get("jd")

    if not file:
        return JsonResponse({"error": "No JD uploaded"}, status=400)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    fname = f"{uuid.uuid4()}_{file.name}"
    path = os.path.join(UPLOAD_DIR, fname)

    with open(path, "wb+") as f:
        for c in file.chunks():
            f.write(c)

    # AUTO INGEST → creates temp master + session
    session = ingest_document(path)

    SESSIONS[session.session_id] = session

    q = get_next_question(session)

    return JsonResponse({
        "session_id": session.session_id,
        "question": q,
        "audio": synthesize_to_base64(q["text"]),
        "finished": False,
    })


# =====================================================
# START PREDEFINED ROLE MODE
# =====================================================

@csrf_exempt
def api_start(request):

    data = json.loads(request.body)

    role_id = data.get("designation")
    role_label = data.get("role_label")

    if not role_id:
        return JsonResponse({"error": "No role selected"}, status=400)

    # create fresh session
    from core.services.session_store import create_session

    session = create_session(
        company=data.get("company", "KnowCraft"),
        role_label=role_label,
        designation=role_id,
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
def api_next(request):

    data = json.loads(request.body)

    session_id = data.get("session_id")
    answer = data.get("answer", "")

    session = SESSIONS.get(session_id)

    if not session:
        return JsonResponse({"error": "Invalid session"}, status=400)

    session.last_answer = answer

    q = get_next_question(session)

    return JsonResponse({
        "question": q,
        "audio": synthesize_to_base64(q["text"]),
        "finished": getattr(session, "finished", False),
    })


# =====================================================
# PREDEFINED ROLE SUPPORT (MASTER FILE READER)
# =====================================================

MASTER_FILE = os.path.join(
    settings.BASE_DIR,
    "core",
    "data",
    "master_roles.json"
)


def _load_master_file():

    if not os.path.exists(MASTER_FILE):
        return {"domains": []}

    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def api_domains(request):

    master = _load_master_file()

    return JsonResponse({
        "domains": [
            {
                "id": d["id"],
                "label": d["label"],
            }
            for d in master.get("domains", [])
            if d.get("active")
        ]
    })


def api_roles(request, domain_id):

    master = _load_master_file()

    for d in master.get("domains", []):
        if d["id"] == domain_id:

            return JsonResponse({
                "roles": [
                    {
                        "id": r["id"],
                        "label": r["label"],
                    }
                    for r in d.get("roles", [])
                    if r.get("active")
                ]
            })

    return JsonResponse({"roles": []})
