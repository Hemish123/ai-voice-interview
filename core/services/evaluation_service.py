import json
import re
from core.services.llm_engine import client, DEPLOYMENT
from core.models import InterviewTurn

def evaluate_interview_transcript(session_id, role_label):
    turns = InterviewTurn.objects.filter(session_id=session_id).order_by('question_index')
    
    if not turns.exists():
        return {"score": 0, "feedback": "No questions were answered during this interview."}
        
    transcript_parts = []
    for turn in turns:
        q = turn.question_text.strip()
        a = turn.answer_text.strip() if turn.answer_text else "[No response]"
        transcript_parts.append(f"Interviewer: {q}\nCandidate: {a}")
        
    transcript_text = "\n\n".join(transcript_parts)
    
    system_prompt = (
        "You are an expert technical interviewer and recruiter. "
        "Review the candidate's interview transcript for the target role and calculate an overall screening match score (0 to 100). "
        "Also provide a concise, high-level evaluation feedback (2-3 sentences max) detailing their key strengths and areas of improvement based on their answers.\n"
        "Your response MUST be a valid JSON object with EXACTLY the following format:\n"
        "{\n"
        "  \"score\": <integer_between_0_and_100>,\n"
        "  \"feedback\": \"<concise_feedback_text>\"\n"
        "}\n"
        "Do not include any other text, warnings, or markdown formatting before or after the JSON."
    )
    
    user_prompt = f"Target Role: {role_label}\n\nTranscript:\n{transcript_text}"
    
    try:
        resp = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        
        raw_content = resp.choices[0].message.content.strip()
        
        # Clean markdown code blocks if present
        if raw_content.startswith("```"):
            lines = raw_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_content = "\n".join(lines).strip()
            
        data = json.loads(raw_content)
        score = int(data.get("score", 50))
        feedback = data.get("feedback", "Evaluation complete.")
        return {"score": score, "feedback": feedback}
        
    except Exception as e:
        print(f"Error calling LLM for evaluation: {e}")
        # Return fallback heuristic
        return {"score": 50, "feedback": "Evaluation completed. Thank you for your time."}
