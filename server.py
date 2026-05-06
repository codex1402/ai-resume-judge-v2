import os
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq
from sqlalchemy import select

# Import functions from backend modules
from backend.gatekeeper.resume_parser import extract_text_from_pdf
from backend.gatekeeper.judge import analyze_resume_ats
from backend.storage import (
    AssessmentAnswer,
    AssessmentSession,
    Candidate,
    ResumeSubmission,
    init_db,
    session_scope,
)

# --- 1. CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=api_key) if api_key else None
app = Flask(__name__)

cors_origins_raw = os.getenv("CORS_ORIGINS", "*").strip()
if cors_origins_raw == "*" or not cors_origins_raw:
    CORS(app)
else:
    allowed_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
    CORS(app, resources={r"/*": {"origins": allowed_origins}})

print(f"API Key: {'Loaded' if api_key else 'Missing'}")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

ASSESSMENT_QUESTION_BANK = {
    "PRODUCT": [
        {
            "id": 1,
            "section": "DSA",
            "question": "What is the time complexity of binary search on a sorted array?",
            "options": ["A. O(n)", "B. O(log n)", "C. O(n log n)", "D. O(1)"],
            "correct_answer": "B",
        },
        {
            "id": 2,
            "section": "DSA",
            "question": "Which data structure is best for implementing an LRU cache efficiently?",
            "options": [
                "A. Array + Stack",
                "B. Queue only",
                "C. HashMap + Doubly Linked List",
                "D. Binary Search Tree only",
            ],
            "correct_answer": "C",
        },
        {
            "id": 3,
            "section": "Algorithms",
            "question": "If a hash table has many collisions, what is the most likely impact?",
            "options": [
                "A. Memory usage drops to zero",
                "B. Lookup tends toward O(n)",
                "C. Sorting becomes impossible",
                "D. Hash function is no longer required",
            ],
            "correct_answer": "B",
        },
        {
            "id": 4,
            "section": "System Design",
            "question": "In distributed system design, eventual consistency means:",
            "options": [
                "A. Every read always gets latest write instantly",
                "B. System never allows writes",
                "C. Replicas may temporarily differ but converge over time",
                "D. Database is always strongly consistent without trade-offs",
            ],
            "correct_answer": "C",
        },
        {
            "id": 5,
            "section": "Performance",
            "question": "Which approach helps reduce latency for read-heavy product features?",
            "options": [
                "A. Remove indexes from DB tables",
                "B. Use caching close to application",
                "C. Increase network hops intentionally",
                "D. Force all traffic to single database node",
            ],
            "correct_answer": "B",
        },
    ],
    "SERVICE": [
        {
            "id": 1,
            "section": "Passage-Based Reasoning",
            "question": "Passage: A support team reports API latency spikes only at 9 AM daily after deployment. Logs show DB connection pool saturation and retries. What is the most probable first root cause to investigate?",
            "options": ["A. CSS rendering bug", "B. Morning traffic burst exhausting DB pool", "C. DNS records deleted", "D. Random browser cache issue"],
            "correct_answer": "B",
        },
        {
            "id": 2,
            "section": "Reasoning",
            "question": "If Module A depends on B and C, and B fails in staging only, what is the best first engineering action?",
            "options": ["A. Rewrite all modules", "B. Isolate B with targeted tests and logs", "C. Disable monitoring", "D. Roll forward without checks"],
            "correct_answer": "B",
        },
        {
            "id": 3,
            "section": "SQL/Backend",
            "question": "Which SQL clause should be used to filter aggregated rows (e.g., count per user > 5)?",
            "options": ["A. WHERE", "B. JOIN", "C. HAVING", "D. DISTINCT"],
            "correct_answer": "C",
        },
        {
            "id": 4,
            "section": "API Basics",
            "question": "What is the main meaning of HTTP 404 in a REST API context?",
            "options": [
                "A. Unauthorized access",
                "B. Resource not found",
                "C. Internal server crash only",
                "D. Request successful with no body",
            ],
            "correct_answer": "B",
        },
        {
            "id": 5,
            "section": "Coding Logic",
            "question": "In debugging a failing service endpoint, what should be done first?",
            "options": [
                "A. Rewrite the full module",
                "B. Add random delays",
                "C. Reproduce and isolate the issue",
                "D. Disable all logs permanently",
            ],
            "correct_answer": "C",
        },
    ],
    "STARTUP": [
        {
            "id": 1,
            "section": "Frontend Practical",
            "question": "In React, what is the purpose of the `key` prop when rendering lists?",
            "options": [
                "A. Encrypt component props",
                "B. Help React identify changed elements efficiently",
                "C. Enable backend authentication",
                "D. Force full rerender every time",
            ],
            "correct_answer": "B",
        },
        {
            "id": 2,
            "section": "Deployment",
            "question": "Which is a practical first step before deploying a web app MVP?",
            "options": [
                "A. Remove environment variables",
                "B. Add health checks and basic logging",
                "C. Skip testing to move faster",
                "D. Disable error handling",
            ],
            "correct_answer": "B",
        },
        {
            "id": 3,
            "section": "Git Workflow",
            "question": "What does `git rebase` primarily do?",
            "options": [
                "A. Deletes remote branches only",
                "B. Rewrites commit base to create cleaner linear history",
                "C. Encrypts repository files",
                "D. Replaces merge conflicts with defaults",
            ],
            "correct_answer": "B",
        },
        {
            "id": 4,
            "section": "Production Reliability",
            "question": "For startup systems, why is monitoring critical early?",
            "options": [
                "A. It reduces need for product decisions",
                "B. It identifies failures and bottlenecks before user churn",
                "C. It removes need for QA",
                "D. It guarantees zero bugs",
            ],
            "correct_answer": "B",
        },
        {
            "id": 5,
            "section": "Backend Scale",
            "question": "Which backend pattern is useful for scaling independent features quickly?",
            "options": [
                "A. Monolithic shared global state only",
                "B. Stateless API services with external persistence",
                "C. Hardcoded credentials in source",
                "D. Single thread for all requests",
            ],
            "correct_answer": "B",
        },
    ],
}

TRACK_TIME_LIMITS = {
    "PRODUCT": 35 * 60,
    "SERVICE": 30 * 60,
    "STARTUP": 25 * 60,
}

INTERVIEWER_OPENERS = {
    "PRODUCT": "Tell me about the most technically challenging project on your resume. I want the problem, the data structures or algorithms involved, and the complexity trade-offs you considered.",
    "SERVICE": "Walk me through a project or internship where you had to debug an issue across frontend, backend, or database layers. What signals did you use to isolate the cause?",
    "STARTUP": "Pick a project you shipped end-to-end. What did you build first, what did you cut from scope, and how did you know the MVP was useful?",
}


def _normalize_track(track_value):
    track = (track_value or "").strip().upper()
    aliases = {
        "PRODUCT": "PRODUCT",
        "SERVICE": "SERVICE",
        "STARTUP": "STARTUP",
        "INCUBATOR": "STARTUP",
        "INCUBATOR_STARTUP": "STARTUP",
    }
    return aliases.get(track, "")


def _extract_json_object(text):
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else None


def _extract_email(text):
    if not text:
        return None
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return m.group(0).lower() if m else None


def _get_or_create_candidate(session, full_name, email):
    candidate = None
    if email:
        candidate = session.scalar(select(Candidate).where(Candidate.email == email))
    if candidate is None:
        candidate = Candidate(full_name=full_name or "Unknown", email=email)
        session.add(candidate)
        session.flush()
    elif full_name and full_name != "Unknown":
        candidate.full_name = full_name
    return candidate


def _build_dynamic_questions(resume_text, track):
    fallback = [
        {
            "id": 6,
            "question": f"For the {track} track, walk through your strongest project end-to-end. Explain architecture, constraints, trade-offs, and one measurable improvement you would implement in the next sprint.",
        },
        {
            "id": 7,
            "question": f"For the {track} track, write pseudocode or production-ready logic for a realistic feature from your resume projects, then justify complexity, error handling, and test strategy.",
        },
    ]

    if not groq_client:
        return fallback

    track_instructions = {
        "PRODUCT": "Make questions hard. At least one should include DSA reasoning + complexity analysis and one should include scalable system design trade-offs.",
        "SERVICE": "Make questions moderate. Include one passage/case-based troubleshooting question and one practical coding/debugging question used in service-company screening.",
        "STARTUP": "Make questions practical and execution-heavy. Focus on shipping MVPs, debugging production issues, and deployment trade-offs.",
    }

    prompt = f"""You are a harsh senior technical interviewer.
Generate exactly 2 personalized deep-dive interview questions for this candidate.
The questions MUST be heavily tied to resume evidence and the selected track.

TRACK: {track}
TRACK REQUIREMENTS: {track_instructions.get(track, '')}
RESUME:
{(resume_text or "")[:7000]}

Rules:
- Return JSON only.
- No markdown.
- No explanations.
- Each question should be 50-120 words and technically deep.
- At least one question must include coding/system design constraints.
- Questions must be different in angle (one architecture/problem-solving, one implementation/debugging/scale).

Return this exact schema:
{{
  "dynamic_questions": [
    {{ "question": "..." }},
    {{ "question": "..." }}
  ]
}}
"""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.45,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content if response and response.choices else ""
        obj_text = _extract_json_object(raw) or raw
        data = json.loads(obj_text)
        questions = data.get("dynamic_questions", [])
        if not isinstance(questions, list) or len(questions) < 2:
            return fallback
        cleaned = []
        for idx, q in enumerate(questions[:2], start=6):
            question_text = (q.get("question") if isinstance(q, dict) else str(q)).strip()
            if not question_text:
                question_text = fallback[idx - 6]["question"]
            cleaned.append({"id": idx, "question": question_text})
        return cleaned
    except Exception as err:
        print(f"Dynamic question generation failed: {type(err).__name__}: {err}")
        return fallback


def _grade_subjective_answers(track, resume_text, question_answer_pairs):
    if not question_answer_pairs:
        return {"score": 0, "max_score": 40, "details": []}

    fallback_details = []
    total = 0
    for idx, pair in enumerate(question_answer_pairs, start=1):
        ans = (pair.get("answer") or "").strip()
        length_bonus = 10 if len(ans) > 250 else 5 if len(ans) > 80 else 0
        tech_bonus = 5 if any(k in ans.lower() for k in ["complexity", "latency", "cache", "index", "trade-off", "scal"]) else 0
        score = min(20, length_bonus + tech_bonus)
        total += score
        fallback_details.append({
            "id": pair.get("id", idx + 5),
            "score": score,
            "max_score": 20,
            "feedback": "Increase technical depth with concrete architecture, constraints, and measurable outcomes."
        })

    if not groq_client:
        return {"score": total, "max_score": 40, "details": fallback_details}

    rubric_prompt = f"""Evaluate candidate answers for a {track} technical assessment.
You must score each answer out of 20 using this rubric:
- Technical correctness (0-8)
- Depth and trade-off reasoning (0-6)
- Practical realism and implementation clarity (0-6)

Candidate Resume (context):
{(resume_text or "")[:5000]}

Question/Answer Pairs:
{json.dumps(question_answer_pairs, ensure_ascii=False)}

Return JSON only:
{{
  "details": [
    {{"id": 6, "score": 0, "max_score": 20, "feedback": "..."}},
    {{"id": 7, "score": 0, "max_score": 20, "feedback": "..."}}
  ]
}}
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": rubric_prompt}],
            temperature=0.2,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content if response and response.choices else ""
        data = json.loads(_extract_json_object(raw) or raw)
        details = data.get("details", [])
        if not isinstance(details, list) or len(details) == 0:
            return {"score": total, "max_score": 40, "details": fallback_details}
        normalized = []
        running = 0
        for idx, item in enumerate(details[:2], start=0):
            score = int(item.get("score", 0))
            score = max(0, min(score, 20))
            running += score
            normalized.append({
                "id": int(item.get("id", 6 + idx)),
                "score": score,
                "max_score": 20,
                "feedback": str(item.get("feedback", "")).strip() or "Answer needs deeper technical reasoning.",
            })
        return {"score": running, "max_score": 40, "details": normalized}
    except Exception as err:
        print(f"Subjective grading fallback: {type(err).__name__}: {err}")
        return {"score": total, "max_score": 40, "details": fallback_details}


def _fallback_interviewer_reply(track, resume_text, messages):
    candidate_messages = [
        str(m.get("content", "")).strip()
        for m in messages
        if isinstance(m, dict) and m.get("role") == "candidate"
    ]
    last_answer = candidate_messages[-1] if candidate_messages else ""

    if not last_answer:
        return {
            "message": INTERVIEWER_OPENERS.get(track, INTERVIEWER_OPENERS["PRODUCT"]),
            "feedback": "Start with a concise project summary, then go deeper into decisions, constraints, and proof of impact.",
            "score": None,
            "stage": "question",
        }

    answer_lower = last_answer.lower()
    score = 45
    if len(last_answer) > 120:
        score += 15
    if len(last_answer) > 300:
        score += 10
    if any(k in answer_lower for k in ["trade", "complexity", "latency", "scale", "test", "metric", "user", "deploy"]):
        score += 15
    score = min(score, 85)

    followups = {
        "PRODUCT": "Good. Now make it concrete: what was the bottleneck, what complexity did your chosen approach have, and what would break first at 10x input size?",
        "SERVICE": "Good. Now explain how you would reproduce that issue in staging and what logs, tests, or database checks you would add before shipping the fix.",
        "STARTUP": "Good. Now tell me the first production risk you would address, the fastest validation experiment, and one metric you would track after launch.",
    }

    return {
        "message": followups.get(track, followups["PRODUCT"]),
        "feedback": "Fallback evaluation: add more evidence, measurable impact, and explicit reasoning about trade-offs.",
        "score": score,
        "stage": "follow_up",
    }


def _build_interviewer_reply(track, resume_text, candidate_name, messages):
    if not groq_client:
        return _fallback_interviewer_reply(track, resume_text, messages)

    transcript = []
    for item in messages[-10:]:
        if not isinstance(item, dict):
            continue
        role = "Candidate" if item.get("role") == "candidate" else "Interviewer"
        content = str(item.get("content", "")).strip()
        if content:
            transcript.append(f"{role}: {content}")

    prompt = f"""You are a senior AI technical interviewer for entry-level software engineering candidates.
Run a realistic interview for the selected hiring track. Use the resume evidence and the transcript.

Candidate: {candidate_name or "Unknown"}
Track: {track}
Resume:
{(resume_text or "")[:5000]}

Transcript:
{chr(10).join(transcript) if transcript else "No messages yet."}

Rules:
- If there is no candidate answer yet, ask one strong opening question tied to resume evidence.
- If the candidate answered, give short feedback and ask exactly one sharper follow-up question.
- Stay professional, specific, and interview-like.
- Do not reveal scoring rubrics or mention JSON.
- Score only when the candidate has answered at least once.

Return JSON only:
{{
  "message": "interviewer question or follow-up",
  "feedback": "1-2 sentence private feedback for the candidate",
  "score": null,
  "stage": "question"
}}
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
            max_tokens=700,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content if response and response.choices else ""
        data = json.loads(_extract_json_object(raw) or raw)
        message = str(data.get("message", "")).strip()
        if not message:
            return _fallback_interviewer_reply(track, resume_text, messages)

        score = data.get("score")
        if score is not None:
            try:
                score = max(0, min(100, int(score)))
            except (TypeError, ValueError):
                score = None

        return {
            "message": message,
            "feedback": str(data.get("feedback", "")).strip(),
            "score": score,
            "stage": str(data.get("stage", "follow_up")).strip() or "follow_up",
        }
    except Exception as err:
        print(f"AI interviewer fallback: {type(err).__name__}: {err}")
        return _fallback_interviewer_reply(track, resume_text, messages)


def _iso(dt):
    return dt.isoformat() if dt else None

# --- 2. THE SERVER ROUTES ---

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    selected_track = _normalize_track(request.form.get("track")) or "PRODUCT"

    try:
        # Extract text from PDF
        text = extract_text_from_pdf(filepath)
        
        if not text:
            return jsonify({
                "error": "Could not extract text from PDF",
                "candidate_name": "Error",
                "overall_score": 0,
                "verdict": "ERROR"
            }), 400
        
        # Run the ATS Analysis
        result = analyze_resume_ats(text)
        result["resume_text"] = text
        candidate_name = result.get("candidate_name", "Unknown")
        email = _extract_email(text)

        with session_scope() as session:
            candidate = _get_or_create_candidate(session, candidate_name, email)
            submission = ResumeSubmission(
                candidate_id=candidate.id,
                file_name=file.filename,
                track=selected_track,
                resume_text=text,
                ats_score=int(result.get("overall_score", 0) or 0),
                ats_verdict=str(result.get("verdict", "")),
                ats_payload=json.dumps(result, ensure_ascii=False),
            )
            session.add(submission)
            session.flush()

            result["candidate_id"] = candidate.id
            result["resume_submission_id"] = submission.id

        return jsonify(result)
    
    except Exception as e:
        print(f"Server Error: {type(e).__name__}: {e}")
        return jsonify({
            "error": str(e),
            "candidate_name": "Server Error",
            "overall_score": 0,
            "verdict": "ERROR"
        }), 500


@app.route('/generate_assessment', methods=['POST'])
def generate_assessment():
    payload = request.get_json(silent=True) or {}
    resume_text = (payload.get("resume_text") or "").strip()
    track = _normalize_track(payload.get("track"))
    candidate_id = payload.get("candidate_id")
    resume_submission_id = payload.get("resume_submission_id")

    if not resume_text:
        return jsonify({"error": "Missing resume_text"}), 400
    if not track:
        return jsonify({"error": "Invalid track. Use PRODUCT, SERVICE, or STARTUP"}), 400

    mcqs = ASSESSMENT_QUESTION_BANK[track]
    dynamic_questions = _build_dynamic_questions(resume_text, track)

    response_payload = {
        "track": track,
        "mcqs": mcqs,
        "dynamic_questions": dynamic_questions,
    }

    with session_scope() as session:
        if resume_submission_id:
            sub = session.get(ResumeSubmission, int(resume_submission_id))
            if sub:
                resume_submission_id = sub.id
                candidate_id = sub.candidate_id
            else:
                resume_submission_id = None
        if candidate_id:
            cand = session.get(Candidate, int(candidate_id))
            candidate_id = cand.id if cand else None

        assessment_session = AssessmentSession(
            candidate_id=candidate_id,
            resume_submission_id=resume_submission_id,
            track=track,
            status="generated",
            time_limit_sec=TRACK_TIME_LIMITS.get(track, 0),
            assessment_payload=json.dumps(response_payload, ensure_ascii=False),
        )
        session.add(assessment_session)
        session.flush()
        response_payload["assessment_session_id"] = assessment_session.id
        response_payload["time_limit_sec"] = assessment_session.time_limit_sec

    return jsonify(response_payload)


@app.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    payload = request.get_json(silent=True) or {}
    track = _normalize_track(payload.get("track"))
    resume_text = (payload.get("resume_text") or "").strip()
    assessment_session_id = payload.get("assessment_session_id")
    mcq_answers = payload.get("mcq_answers") or []
    subjective_answers = payload.get("subjective_answers") or []
    violations = int(payload.get("violations", 0) or 0)
    auto_submitted = bool(payload.get("auto_submitted", False))
    time_taken_sec = int(payload.get("time_taken_sec", 0) or 0)

    if not track:
        return jsonify({"error": "Invalid track"}), 400

    question_bank = ASSESSMENT_QUESTION_BANK[track]
    answer_map = {int(a.get("id")): str(a.get("selected_answer", "")).strip().upper() for a in mcq_answers if isinstance(a, dict) and a.get("id")}

    mcq_details = []
    correct_count = 0
    for q in question_bank:
        selected = answer_map.get(q["id"], "")
        is_correct = selected == q["correct_answer"]
        if is_correct:
            correct_count += 1
        mcq_details.append({
            "id": q["id"],
            "section": q.get("section", ""),
            "selected_answer": selected,
            "correct_answer": q["correct_answer"],
            "is_correct": is_correct,
        })

    mcq_score = int((correct_count / 5) * 60)

    qa_pairs = []
    for item in subjective_answers:
        if not isinstance(item, dict):
            continue
        qa_pairs.append({
            "id": item.get("id"),
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
        })
    subjective = _grade_subjective_answers(track, resume_text, qa_pairs)
    subjective_score = int(subjective.get("score", 0))

    penalty = min(15, violations * 3)
    final_score = max(0, min(100, mcq_score + subjective_score - penalty))

    verdict = "REJECT"
    if final_score >= 75:
        verdict = "SHORTLIST"
    elif final_score >= 60:
        verdict = "BORDERLINE"

    response_payload = {
        "track": track,
        "final_score": final_score,
        "verdict": verdict,
        "breakdown": {
            "mcq_score": mcq_score,
            "mcq_max": 60,
            "subjective_score": subjective_score,
            "subjective_max": 40,
            "violation_penalty": penalty,
            "violations": violations,
            "auto_submitted": auto_submitted,
            "time_taken_sec": time_taken_sec,
        },
        "mcq_details": mcq_details,
        "subjective_details": subjective.get("details", []),
    }

    with session_scope() as session:
        assessment_session = None
        if assessment_session_id:
            assessment_session = session.get(AssessmentSession, int(assessment_session_id))

        if assessment_session is None:
            assessment_session = AssessmentSession(
                track=track,
                status="completed",
                time_limit_sec=TRACK_TIME_LIMITS.get(track, 0),
            )
            session.add(assessment_session)
            session.flush()

        assessment_session.track = track
        assessment_session.status = "completed"
        assessment_session.violations = violations
        assessment_session.time_taken_sec = time_taken_sec
        assessment_session.auto_submitted = auto_submitted
        assessment_session.mcq_score = mcq_score
        assessment_session.subjective_score = subjective_score
        assessment_session.penalty = penalty
        assessment_session.final_score = final_score
        assessment_session.verdict = verdict
        assessment_session.result_payload = json.dumps(response_payload, ensure_ascii=False)

        old_answers = session.scalars(
            select(AssessmentAnswer).where(AssessmentAnswer.assessment_session_id == assessment_session.id)
        ).all()
        for old in old_answers:
            session.delete(old)

        question_map = {q["id"]: q for q in question_bank}
        for item in mcq_details:
            q = question_map.get(item["id"], {})
            session.add(
                AssessmentAnswer(
                    assessment_session_id=assessment_session.id,
                    question_id=int(item["id"]),
                    question_type="mcq",
                    question_text=q.get("question"),
                    selected_answer=item.get("selected_answer"),
                    correct_answer=item.get("correct_answer"),
                    is_correct=bool(item.get("is_correct")),
                    score=12 if item.get("is_correct") else 0,
                    max_score=12,
                )
            )

        subjective_map = {int(i.get("id")): i for i in subjective_answers if isinstance(i, dict) and i.get("id")}
        for detail in response_payload["subjective_details"]:
            qid = int(detail.get("id", 0))
            source = subjective_map.get(qid, {})
            session.add(
                AssessmentAnswer(
                    assessment_session_id=assessment_session.id,
                    question_id=qid,
                    question_type="subjective",
                    question_text=source.get("question"),
                    answer_text=source.get("answer"),
                    score=int(detail.get("score", 0)),
                    max_score=int(detail.get("max_score", 20)),
                    feedback=detail.get("feedback"),
                )
            )

        response_payload["assessment_session_id"] = assessment_session.id

    return jsonify(response_payload)


@app.route('/ai_interviewer', methods=['POST'])
def ai_interviewer():
    payload = request.get_json(silent=True) or {}
    track = _normalize_track(payload.get("track")) or "PRODUCT"
    resume_text = (payload.get("resume_text") or "").strip()
    candidate_name = (payload.get("candidate_name") or "Candidate").strip()
    messages = payload.get("messages") or []

    if not isinstance(messages, list):
        return jsonify({"error": "messages must be a list"}), 400
    if not resume_text:
        return jsonify({"error": "Missing resume_text"}), 400

    reply = _build_interviewer_reply(track, resume_text, candidate_name, messages)
    return jsonify({
        "track": track,
        "candidate_name": candidate_name,
        "reply": reply,
    })


@app.route('/candidate_history/<int:candidate_id>', methods=['GET'])
def candidate_history(candidate_id):
    with session_scope() as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            return jsonify({"error": "Candidate not found"}), 404

        submissions = session.scalars(
            select(ResumeSubmission).where(ResumeSubmission.candidate_id == candidate_id)
        ).all()
        sessions = session.scalars(
            select(AssessmentSession).where(AssessmentSession.candidate_id == candidate_id)
        ).all()

        submissions = sorted(submissions, key=lambda s: s.created_at or "", reverse=True)
        sessions = sorted(sessions, key=lambda s: s.created_at or "", reverse=True)

        response_payload = {
            "candidate": {
                "id": candidate.id,
                "full_name": candidate.full_name,
                "email": candidate.email,
                "created_at": _iso(candidate.created_at),
                "updated_at": _iso(candidate.updated_at),
            },
            "resume_submissions": [
                {
                    "id": s.id,
                    "file_name": s.file_name,
                    "track": s.track,
                    "ats_score": s.ats_score,
                    "ats_verdict": s.ats_verdict,
                    "created_at": _iso(s.created_at),
                }
                for s in submissions
            ],
            "assessment_sessions": [
                {
                    "id": a.id,
                    "resume_submission_id": a.resume_submission_id,
                    "track": a.track,
                    "status": a.status,
                    "final_score": a.final_score,
                    "verdict": a.verdict,
                    "violations": a.violations,
                    "auto_submitted": a.auto_submitted,
                    "time_taken_sec": a.time_taken_sec,
                    "created_at": _iso(a.created_at),
                    "updated_at": _iso(a.updated_at),
                }
                for a in sessions
            ],
        }

    return jsonify(response_payload)


@app.route('/assessment_session/<int:session_id>', methods=['GET'])
def assessment_session_detail(session_id):
    with session_scope() as session:
        assessment = session.get(AssessmentSession, session_id)
        if not assessment:
            return jsonify({"error": "Assessment session not found"}), 404

        answers = session.scalars(
            select(AssessmentAnswer).where(AssessmentAnswer.assessment_session_id == session_id)
        ).all()
        answers = sorted(answers, key=lambda a: (a.question_type or "", a.question_id))

        response_payload = {
            "assessment_session": {
                "id": assessment.id,
                "candidate_id": assessment.candidate_id,
                "resume_submission_id": assessment.resume_submission_id,
                "track": assessment.track,
                "status": assessment.status,
                "time_limit_sec": assessment.time_limit_sec,
                "time_taken_sec": assessment.time_taken_sec,
                "violations": assessment.violations,
                "auto_submitted": assessment.auto_submitted,
                "mcq_score": assessment.mcq_score,
                "subjective_score": assessment.subjective_score,
                "penalty": assessment.penalty,
                "final_score": assessment.final_score,
                "verdict": assessment.verdict,
                "created_at": _iso(assessment.created_at),
                "updated_at": _iso(assessment.updated_at),
            },
            "answers": [
                {
                    "id": a.id,
                    "question_id": a.question_id,
                    "question_type": a.question_type,
                    "question_text": a.question_text,
                    "selected_answer": a.selected_answer,
                    "correct_answer": a.correct_answer,
                    "is_correct": a.is_correct,
                    "answer_text": a.answer_text,
                    "score": a.score,
                    "max_score": a.max_score,
                    "feedback": a.feedback,
                    "created_at": _iso(a.created_at),
                }
                for a in answers
            ],
        }

    return jsonify(response_payload)


@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    print(f"Entry-Level ATS Server Running on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
