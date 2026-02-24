import os
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq

# Import functions from backend modules
from backend.gatekeeper.resume_parser import extract_text_from_pdf
from backend.gatekeeper.judge import analyze_resume_ats

# --- 1. CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=api_key) if api_key else None
app = Flask(__name__)
CORS(app)  # Allow Frontend connection

print(f"API Key: {'Loaded' if api_key else 'Missing'}")

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

    if not resume_text:
        return jsonify({"error": "Missing resume_text"}), 400
    if not track:
        return jsonify({"error": "Invalid track. Use PRODUCT, SERVICE, or STARTUP"}), 400

    mcqs = ASSESSMENT_QUESTION_BANK[track]
    dynamic_questions = _build_dynamic_questions(resume_text, track)

    return jsonify({
        "track": track,
        "mcqs": mcqs,
        "dynamic_questions": dynamic_questions,
    })


@app.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    payload = request.get_json(silent=True) or {}
    track = _normalize_track(payload.get("track"))
    resume_text = (payload.get("resume_text") or "").strip()
    mcq_answers = payload.get("mcq_answers") or []
    subjective_answers = payload.get("subjective_answers") or []
    violations = int(payload.get("violations", 0) or 0)
    auto_submitted = bool(payload.get("auto_submitted", False))
    time_taken_sec = int(payload.get("time_taken_sec", 0) or 0)

    if not track:
        return jsonify({"error": "Invalid track"}), 400

    question_bank = ASSESSMENT_QUESTION_BANK[track]
    answer_key = {q["id"]: q["correct_answer"] for q in question_bank}
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

    return jsonify({
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
    })

if __name__ == '__main__':
    print("Entry-Level ATS Server Running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
