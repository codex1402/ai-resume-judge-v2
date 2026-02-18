"""
AI Hiring Lab - Entry-Level ATS Resume Analyzer
Uses Groq to analyze resumes for entry-level/new graduate software engineering roles
"""

import os
import json
import re
import time
from groq import Groq
from dotenv import load_dotenv


def _extract_first_json_object(text: str) -> str | None:
    """
    Extract the first top-level JSON object from text by matching braces while
    respecting string literals and escapes.
    """
    if not text:
        return None

    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _is_quota_error(exc: Exception) -> bool:
    s = str(exc).lower()
    r = repr(exc).lower()
    return (
        "429" in s
        or "429" in r
        or "quota" in s
        or "rate limit" in s
        or "resource_exhausted" in s
    )


def _is_auth_error(exc: Exception) -> bool:
    s = str(exc).lower()
    r = repr(exc).lower()
    return (
        "401" in s
        or "401" in r
        or "unauthorized" in s
        or "invalid api key" in s
        or "authentication" in s
    )


def _is_model_not_found_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return ("404" in s and "not_found" in s) or "model" in s and "is not found" in s


PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]


def _discover_model_candidates(client_obj):
    """
    Resolve valid model candidates for the current account/API version.
    """
    try:
        available = set()
        model_list = client_obj.models.list()
        model_data = getattr(model_list, "data", []) or []
        for model in model_data:
            name = getattr(model, "id", "")
            if not name:
                continue
            available.add(name)

        resolved = [m for m in PREFERRED_MODELS if m in available]
        if resolved:
            print(f"Model candidates resolved: {', '.join(resolved)}")
            return resolved
    except Exception as model_list_err:
        print(f"Model discovery failed, using defaults: {model_list_err}")

    return PREFERRED_MODELS[:]


def _repair_common_json_issues(text: str) -> str:
    """
    Best-effort repair for common LLM JSON mistakes:
    - trailing commas before } or ]
    - smart quotes
    - leading/trailing junk
    """
    if not text:
        return text

    repaired = text.strip()

    # Normalize “smart quotes” if any
    repaired = repaired.replace("“", '"').replace("”", '"').replace("’", "'")

    # Remove trailing commas:  { "a": 1, }  or  [1,2,]
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    return repaired


def _salvage_minimal_ats_payload(text: str) -> dict:
    """
    Build a minimal valid ATS payload from a truncated response.
    """
    name = "Unknown"
    score = 0
    verdict = "ERROR"

    try:
        m = re.search(r'"candidate_name"\s*:\s*"([^"]*)', text)
        if m and m.group(1).strip():
            name = m.group(1).strip()
    except Exception:
        pass

    try:
        m = re.search(r'"overall_score"\s*:\s*(\d+)', text)
        if m:
            score = int(m.group(1))
    except Exception:
        pass

    try:
        m = re.search(r'"verdict"\s*:\s*"([^"]*)', text)
        if m:
            raw = m.group(1).strip().lower()
            if raw.startswith("short"):
                verdict = "Shortlist"
            elif raw.startswith("border"):
                verdict = "Borderline"
            elif raw.startswith("reject"):
                verdict = "Reject"
    except Exception:
        pass

    return {
        "candidate_name": name,
        "overall_score": score,
        "verdict": verdict,
        "track_scores": {
            "product_based": score,
            "service_based": score,
            "incubator_startup": score,
        },
        "detailed_analysis": {
            "strengths": [],
            "weaknesses": [
                "Model response was truncated before full JSON could be returned."
            ],
            "actionable_improvements": [
                "Retry once. If it repeats, shorten resume text or reduce traffic."
            ],
        },
        "interview_questions": {
            "technical": "None",
            "behavioral": "None",
        },
    }


def _salvage_without_detailed_analysis(text: str) -> dict | None:
    """
    Best-effort salvage: keep candidate_name, overall_score, verdict, track_scores
    and replace detailed_analysis + interview_questions with minimal defaults.
    Used only when JSON is truncated inside detailed_analysis.
    """
    try:
        idx = text.find('"detailed_analysis"')
        if idx == -1:
            return None

        # Keep everything before detailed_analysis, trimming trailing comma/newlines
        prefix = text[:idx].rstrip()
        if prefix.endswith(","):
            prefix = prefix[:-1]

        # Build a minimal, syntactically complete JSON string
        minimal_tail = (
            '"detailed_analysis": {'
            '"strengths": [],'
            '"weaknesses": [],'
            '"actionable_improvements": []'
            '},'
            '"interview_questions": {'
            '"technical": "",'
            '"behavioral": ""'
            '}'
            "}"
        )

        # Ensure prefix ends just before the last closing brace of the root object
        if prefix.strip().endswith("{"):
            json_text = prefix + minimal_tail
        else:
            # Remove any trailing trailing characters after the last comma
            last_comma = prefix.rfind(",")
            last_brace = prefix.rfind("{")
            if last_comma > last_brace:
                prefix = prefix[: last_comma + 1]
            json_text = prefix + minimal_tail

        return json.loads(_repair_common_json_issues(json_text))
    except Exception:
        return None


def _normalize_to_ats_schema(data: dict) -> dict:
    """
    Normalize common model/schema deviations into the ATS schema expected by the UI.
    This prevents UI breakage if the model accidentally responds with the legacy schema.
    """
    if not isinstance(data, dict):
        return data

    # Already ATS schema
    if "overall_score" in data and "track_scores" in data and "detailed_analysis" in data:
        return data

    # Legacy schema (from old judge): signal_score/red_flags/brutal_feedback/interview_question
    if "signal_score" in data and ("red_flags" in data or "brutal_feedback" in data):
        score = data.get("signal_score", 0)
        verdict_raw = (data.get("verdict") or "").strip()
        verdict = "Reject"
        if verdict_raw.upper() in {"PASS", "SHORTLIST"}:
            verdict = "Shortlist"
        elif verdict_raw.upper() in {"BORDERLINE"}:
            verdict = "Borderline"
        elif verdict_raw.upper() in {"REJECTED", "REJECT"}:
            verdict = "Reject"
        elif verdict_raw.upper() in {"ERROR"}:
            verdict = "ERROR"

        weaknesses = data.get("red_flags") if isinstance(data.get("red_flags"), list) else []
        technical_q = data.get("interview_question") or "None"

        return {
            "candidate_name": data.get("candidate_name", "Unknown"),
            "overall_score": int(score) if str(score).isdigit() else 0,
            "verdict": verdict,
            "track_scores": {
                "product_based": int(score) if str(score).isdigit() else 0,
                "service_based": int(score) if str(score).isdigit() else 0,
                "incubator_startup": int(score) if str(score).isdigit() else 0,
            },
            "detailed_analysis": {
                "strengths": [],
                "weaknesses": weaknesses if weaknesses else ["Model returned legacy schema; normalized automatically."],
                "actionable_improvements": [],
            },
            "interview_questions": {
                "technical": technical_q,
                "behavioral": "Tell me about a time you worked with a team under a deadline. What did you do?",
            },
        }

    return data


def _guess_candidate_name(resume_text: str) -> str:
    if not resume_text:
        return "Unknown"
    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    if not lines:
        return "Unknown"
    first = lines[0]
    if len(first.split()) <= 5:
        return first[:80]
    return "Unknown"


def _local_ats_fallback(resume_text: str, reason: str = "") -> dict:
    """
    Local non-LLM fallback so analysis still works during API quota outages.
    """
    text = (resume_text or "").lower()
    score = 45
    if "intern" in text:
        score += 12
    if "github" in text:
        score += 8
    if "project" in text:
        score += 8
    if any(k in text for k in ["react", "node", "python", "java", "sql", "api", "docker"]):
        score += 10
    if any(k in text for k in ["leetcode", "codeforces", "dsa", "algorithm"]):
        score += 8
    if any(k in text for k in ["aws", "gcp", "azure", "deploy", "deployed"]):
        score += 6
    score = max(30, min(score, 82))

    verdict = "Reject"
    if score >= 75:
        verdict = "Shortlist"
    elif score >= 60:
        verdict = "Borderline"

    name = _guess_candidate_name(resume_text)

    return {
        "candidate_name": name,
        "overall_score": score,
        "verdict": verdict,
        "track_scores": {
            "product_based": max(0, min(100, score - 2)),
            "service_based": max(0, min(100, score + 2)),
            "incubator_startup": max(0, min(100, score + 1)),
        },
        "detailed_analysis": {
            "strengths": [
                "Detected relevant technical keywords and project-oriented content.",
                "Resume shows baseline entry-level software engineering readiness.",
                "Track scores were generated using ATS-style heuristic checks.",
            ],
            "weaknesses": [
                "Add measurable outcomes for projects and internships.",
                "Include GitHub and deployed links as proof of work.",
                "Clarify ownership, complexity, and impact per experience bullet.",
            ],
            "actionable_improvements": [
                "[Product] Add DSA profile link and solved problems count.",
                "[Service] Quantify internship/project outcomes with clear metrics.",
                "[Startup] Add deployed links, demo video, and README proof.",
            ],
        },
        "interview_questions": {
            "technical": "Explain one project architecture and tradeoffs you chose.",
            "behavioral": "Describe a tight-deadline collaboration and your contribution.",
        },
    }

# Load environment
load_dotenv()
_primary_key = (os.getenv("GROQ_API_KEY") or "").strip()
_extra_keys_raw = (os.getenv("GROQ_API_KEYS") or "").strip()
_all_keys = [_primary_key] + [k.strip() for k in _extra_keys_raw.split(",") if k.strip()]
api_keys = list(dict.fromkeys([k for k in _all_keys if k]))
api_key = api_keys[0] if api_keys else ""
clients = [Groq(api_key=k) for k in api_keys]
model_candidates_configured = _discover_model_candidates(clients[0]) if clients else PREFERRED_MODELS[:]
_quota_cooldown_until = 0.0

print(f"API keys loaded: {len(api_keys)}")


def analyze_resume_ats(resume_text):
    """
    Analyze a resume using an entry-level ATS system.
    
    Args:
        resume_text: Full resume text extracted from PDF
        
    Returns:
        dict with detailed ATS analysis including track scores and recommendations
    """
    
    print(f"\n{'='*60}")
    print("ENTRY-LEVEL ATS ANALYSIS")
    print(f"{'='*60}")
    print(f"Resume length: {len(resume_text)} characters")
    print(f"Preview: {resume_text[:100].replace(chr(10), ' ')}...")

    global _quota_cooldown_until
    now = time.time()
    if now < _quota_cooldown_until:
        remaining = int(_quota_cooldown_until - now)
        print(f"Quota cooldown active ({remaining}s). Using local fallback.")
        return _local_ats_fallback(
            resume_text,
            reason="Quota cooldown active; skipped provider call."
        )
    
    if not clients:
        return {
            "candidate_name": "Error: No API Key",
            "overall_score": 0,
            "verdict": "ERROR",
            "track_scores": {
                "product_based": 0,
                "service_based": 0,
                "incubator_startup": 0
            },
            "detailed_analysis": {
                "strengths": ["System error: Missing API key(s)"],
                "weaknesses": [],
                "actionable_improvements": []
            },
            "interview_questions": {
                "technical": "None",
                "behavioral": "None"
            }
        }
    
    # Entry-level ATS prompt - calibrated for new graduates (2026 market-relevant)
    prompt = f"""You are an expert ATS (Applicant Tracking System) evaluator specializing in Entry-Level and New Graduate Software Engineering roles (0-2 years experience). Your output must be fair, specific, and aligned with real 2026 hiring practices.

CRITICAL CONTEXT:
- Candidate is entry-level/new grad; do NOT expect senior/CTO-level scope.
- ATS scoring should feel realistic: 70-80 = solid hireable, 80-90 = excellent, 90+ = rare.
- Penalize vagueness and missing proof (no links, no metrics), but don't penalize for not having senior titles.
- Prefer evidence: GitHub links, deployed demos, measurable outcomes, internships, open-source activity.

MARKET-RELEVANT SIGNALS (2026 entry-level):
- Strong signals:
  - Deployed projects (live links), clean GitHub repos with READMEs, tests, CI, meaningful commits
  - Internship impact with metrics (latency, users, conversion, cost, throughput) even if small
  - Practical fundamentals: APIs, databases, auth, caching, cloud basics (AWS/GCP/Azure), Docker
  - Modern stack awareness: React/Next, Node/Python/Java, REST/GraphQL, SQL + basic NoSQL
  - Basic DevOps/reliability: logging, monitoring basics, CI/CD, versioning, env management
  - AI familiarity is a plus if practical (LLM API usage, RAG basics, prompt/versioning), not buzzwords
- Red flags:
  - Only tutorial projects with no differentiation (calculator/todo only) AND no deployments/links
  - Claims without proof, no GitHub/LinkedIn, missing project ownership details
  - Completely unquantified internship work ("worked on", "helped with") without outcomes

GAP YEARS / BREAKS (must evaluate):
- Detect gaps between education → internships → full-time (or long breaks within timelines).
- Do NOT auto-reject for gaps. Score impact depends on how well they explain + show upskilling/projects during the gap.
- If a gap exists and is not addressed, include it as a weakness and add a concrete improvement.

SCORING GUIDELINES (Entry-Level Calibration):
- 0-40: Missing fundamentals (no relevant skills/projects)
- 41-55: Below average (thin projects, weak evidence, no internships)
- 56-69: Average entry-level (basic projects, some skills, limited evidence)
- 70-79: Solid entry-level (good projects, relevant skills, some internships or strong portfolio) ← MOST COMMON
- 80-89: Excellent entry-level (deployments + strong internships + evidence + clear depth)
- 90-100: Exceptional entry-level (rare; outstanding impact + strong proof + leadership/OSS)

TRACK-SPECIFIC EVALUATION (score each track independently):

1. PRODUCT-BASED COMPANIES (Google, Amazon, Microsoft, etc.)
   Focus Areas:
   - Data Structures & Algorithms (DSA) knowledge and practice
   - Core Computer Science fundamentals (OS, DBMS, Networks)
   - Problem-solving ability (LeetCode, competitive programming, hackathons)
   - Optimization mindset (mentions of time/space complexity, scalability)
   - Strong technical projects with algorithmic complexity
   
   Scoring Factors:
   - LeetCode/Codeforces/HackerRank profiles: +10-15 points
   - Competitive programming achievements: +5-10 points
   - Projects demonstrating algorithms/data structures: +5-10 points
   - CS fundamentals knowledge: +5-10 points

2. SERVICE-BASED COMPANIES (TCS, Infosys, Wipro, Accenture, etc.)
   Focus Areas:
   - Tech stack breadth (multiple languages/frameworks)
   - Full-stack development capabilities
   - Teamwork and collaboration experience
   - Communication skills (documentation, presentations)
   - Basic deployment and DevOps awareness
   - Professionalism and soft skills
   
   Scoring Factors:
   - Multiple tech stacks mentioned: +5-10 points
   - Full-stack projects: +5-10 points
   - Team projects/collaborations: +5-8 points
   - Internships in service companies: +8-12 points
   - Certifications: +3-5 points

3. INCUBATOR/STARTUP COMPANIES (Y Combinator, Techstars startups, etc.)
   Focus Areas:
   - Hustle and ownership mentality
   - End-to-end project deployments (live links, GitHub)
   - MVP building experience
   - Taking initiative and self-learning
   - Ability to wear multiple hats
   - Real-world problem solving
   
   Scoring Factors:
   - Deployed projects with live links: +10-15 points
   - GitHub with active contributions: +5-10 points
   - Startup internships/experience: +8-12 points
   - Projects solving real problems: +5-10 points
   - Self-taught skills and certifications: +5-8 points

TARGET TRACK INFERENCE:
- Infer which track the candidate is MOST likely targeting based on the resume (skills, companies, wording, projects).
- Even if you infer a target, you MUST provide improvements that are usable for ALL three tracks, labeled clearly.

RESUME TEXT:
{resume_text[:6000]}

CRITICAL INSTRUCTIONS:
1. Extract the candidate's full name from the resume.
2. Use EVIDENCE-BASED SCORING ONLY. Every score must be justified by concrete resume evidence.
3. Apply this scoring formula for overall_score:
   - 30% project depth and execution quality
   - 25% internship/professional impact and quantified outcomes
   - 20% core CS/DSA/problem-solving proof
   - 15% deployment/GitHub/proof-of-work links
   - 10% communication/structure/clarity of resume
4. Penalize missing evidence explicitly:
   - no metrics, no links, vague bullets, unclear ownership, timeline gaps without explanation.
5. Avoid score anchoring:
   - DO NOT default to 75-80.
   - If evidence is weak, score should fall to 45-65.
   - If evidence is strong and quantified, score can be 80+.
6. Determine verdict: "Shortlist" (75+), "Borderline" (60-74), or "Reject" (<60).
7. Score each track independently (product_based, service_based, incubator_startup) on a 0-100 scale.
8. Return 4-6 strengths, 4-6 weaknesses, and 6-9 actionable_improvements.
9. Improvements must be highly specific to this exact resume and include:
   - at least two [Product] improvements
   - at least two [Service] improvements
   - at least two [Startup] improvements
   - one [Gap] improvement if you detect any gap/break
10. Interview questions must be comprehensive and realistic:
   - technical question should include architecture/design tradeoffs and a follow-up constraint
   - behavioral question should include context, conflict, and measurable outcome expectation
   - each question should be 35-90 words
11. Do not use generic advice templates. Reference candidate-specific skills, projects, and missing evidence.
12. Output valid JSON only. No markdown. No extra keys.

Return ONLY valid JSON using this exact schema (no markdown, no explanation):

{{
  "candidate_name": "String - full name from resume",
  "overall_score": 75,
  "verdict": "Shortlist",
  "track_scores": {{
    "product_based": 72,
    "service_based": 78,
    "incubator_startup": 80
  }},
  "detailed_analysis": {{
    "strengths": [
      "Specific strength 1",
      "Specific strength 2",
      "Specific strength 3",
      "Specific strength 4"
    ],
    "weaknesses": [
      "Specific weakness 1",
      "Specific weakness 2",
      "Specific weakness 3"
    ],
    "actionable_improvements": [
      "Concrete improvement 1",
      "Concrete improvement 2",
      "Concrete improvement 3"
    ]
  }},
  "interview_questions": {{
    "technical": "Technical question based on strongest project",
    "behavioral": "Behavioral question based on team/startup experience"
  }}
}}"""

    try:
        print("Calling Groq API with JSON response format...")

        response = None
        auth_errors = 0
        quota_errors = 0
        model_candidates = model_candidates_configured

        for key_index, client in enumerate(clients, start=1):
            key_hit_quota = False
            for model_name in model_candidates:
                try:
                    print(f"Trying key #{key_index} with model {model_name}")
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.35,
                        max_tokens=3200,
                        response_format={"type": "json_object"},
                    )
                    break
                except Exception as api_err:
                    if _is_auth_error(api_err):
                        auth_errors += 1
                        print(f"Auth error on key #{key_index} ({model_name}): {api_err}")
                        continue
                    if _is_quota_error(api_err):
                        quota_errors += 1
                        print(f"Quota/rate error on key #{key_index} ({model_name})")
                        key_hit_quota = True
                        break
                    if _is_model_not_found_error(api_err):
                        print(f"Model unavailable for this API/version: {model_name}")
                        continue
                    raise
            if response is not None:
                break
            if key_hit_quota:
                # Avoid burning requests on additional models for the same key
                # when provider already reported quota/rate exhaustion.
                continue

        if response is None:
            if quota_errors > 0:
                raise ValueError("API_QUOTA_EXCEEDED")
            if auth_errors > 0:
                raise ValueError("API_AUTH_ERROR")
            raise ValueError("API_CALL_FAILED")
        
        print("API response received")

        # Extract text from Groq chat completion
        raw_text = None
        try:
            if response and getattr(response, "choices", None):
                first_choice = response.choices[0]
                message = getattr(first_choice, "message", None)
                if message and getattr(message, "content", None):
                    raw_text = str(message.content).strip()
            if not raw_text:
                raise ValueError("Could not extract text from Groq response - response is empty")
        except (AttributeError, IndexError, KeyError, TypeError) as attr_err:
            print(f"Warning: Error accessing response: {attr_err}")
            raise ValueError(f"Could not extract text from response: {attr_err}")
        
        # Validate we got text
        if not raw_text or len(raw_text.strip()) == 0:
            raise ValueError("Response text is empty")
        
        # Remove any markdown code blocks if present (shouldn't happen with JSON mode, but just in case)
        clean_text = re.sub(r'^```json\s*', '', raw_text, flags=re.MULTILINE)
        clean_text = re.sub(r'\s*```$', '', clean_text, flags=re.MULTILINE)
        clean_text = clean_text.strip()

        # Save raw ATS response for debugging (this is the ATS path, not legacy judge)
        try:
            with open('last_ai_response_ats.txt', 'w', encoding='utf-8') as f:
                f.write(f"Response length: {len(clean_text)}\n")
                f.write("=" * 70 + "\n")
                f.write(clean_text)
                f.write("\n" + "=" * 70 + "\n")
        except Exception:
            pass
        
        print(f"Parsing JSON response... (length: {len(clean_text)} chars)")

        # Parse JSON (with best-effort fallback extraction/repair)
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError as inner_err:
            # 1) Try to extract a balanced JSON object
            extracted = _extract_first_json_object(clean_text)
            if extracted:
                extracted = _repair_common_json_issues(extracted)
                data = json.loads(extracted)
            else:
                # 2) Try to salvage by dropping/neutralizing detailed_analysis section only
                salvaged = _salvage_without_detailed_analysis(clean_text)
                if salvaged is not None:
                    data = salvaged
                else:
                    # 3) Last attempt: repair whole text
                    repaired = _repair_common_json_issues(clean_text)
                    try:
                        data = json.loads(repaired)
                    except json.JSONDecodeError:
                        data = _salvage_minimal_ats_payload(clean_text)

        # Normalize any schema drift (e.g., legacy keys) before validation
        data = _normalize_to_ats_schema(data)
        
        # Validate required fields
        required_fields = ['candidate_name', 'overall_score', 'verdict', 'track_scores', 
                          'detailed_analysis', 'interview_questions']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate track_scores structure
        if 'product_based' not in data['track_scores'] or \
           'service_based' not in data['track_scores'] or \
           'incubator_startup' not in data['track_scores']:
            raise ValueError("track_scores missing required fields")
        
        # Validate detailed_analysis structure
        if 'strengths' not in data['detailed_analysis'] or \
           'weaknesses' not in data['detailed_analysis'] or \
           'actionable_improvements' not in data['detailed_analysis']:
            raise ValueError("detailed_analysis missing required fields")
        
        # Validate interview_questions structure
        if 'technical' not in data['interview_questions'] or \
           'behavioral' not in data['interview_questions']:
            raise ValueError("interview_questions missing required fields")
        
        print("Successfully parsed and validated JSON response")
        print(f"   Candidate: {data.get('candidate_name', 'Unknown')}")
        print(f"   Overall Score: {data.get('overall_score', 0)}/100")
        print(f"   Verdict: {data.get('verdict', 'Unknown')}")
        print(f"{'='*60}\n")
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        excerpt = clean_text[:500] if "clean_text" in locals() else "N/A"
        print(f"Response (first 500 chars): {excerpt}")

        return {
            "candidate_name": "Parse Error",
            "overall_score": 0,
            "verdict": "ERROR",
            "track_scores": {
                "product_based": 0,
                "service_based": 0,
                "incubator_startup": 0
            },
            "detailed_analysis": {
                "strengths": [],
                "weaknesses": [
                    "AI returned invalid JSON format (could not be repaired).",
                    f"Parse error: {str(e)[:150]}"
                ],
                "actionable_improvements": [
                    "Try again (temporary model formatting glitch).",
                    "If it repeats, shorten the resume PDF (remove images) or try a text-based PDF.",
                    "Lower request frequency if you are hitting rate limits."
                ]
            },
            "interview_questions": {
                "technical": "None",
                "behavioral": "None"
            }
        }
        
    except ValueError as e:
        # Handle specific API errors
        error_msg = str(e)
        
        if error_msg == "API_QUOTA_EXCEEDED":
            print("API Quota Exceeded - using local fallback analysis")
            _quota_cooldown_until = time.time() + 600  # 10 minutes
            return _local_ats_fallback(
                resume_text,
                reason="API quota exceeded across available keys/models."
            )
        elif error_msg == "API_AUTH_ERROR":
            print("API Authentication Error - Please check your API key")
            return {
                "candidate_name": "API Auth Error",
                "overall_score": 0,
                "verdict": "ERROR",
                "track_scores": {
                    "product_based": 0,
                    "service_based": 0,
                    "incubator_startup": 0
                },
                "detailed_analysis": {
                    "strengths": [],
                    "weaknesses": [
                        "Invalid or expired API key. Authentication failed with Groq API."
                    ],
                    "actionable_improvements": [
                        "Verify your GROQ_API_KEY in the .env file is correct",
                        "Optionally set GROQ_API_KEYS with comma-separated backup keys",
                        "Check if your API key has expired or been revoked",
                        "Generate a new API key from Groq Console if needed"
                    ]
                },
                "interview_questions": {
                    "technical": "None - API authentication failed",
                    "behavioral": "None - API authentication failed"
                }
            }
        else:
            if error_msg == "API_CALL_FAILED":
                return _local_ats_fallback(
                    resume_text,
                    reason="API call failed for all key/model combinations."
                )
            raise
            
    except Exception as e:
        error_str = str(e).lower()
        error_type = type(e).__name__
        
        # Check for quota/rate limit in the exception message
        is_quota_error = (
            '429' in str(e) or 
            'quota' in error_str or 
            'rate limit' in error_str or 
            'resource_exhausted' in error_str or
            'ClientError' in error_type
        )
        
        print(f"API Error: {error_type}: {e}")
        
        if is_quota_error or _is_model_not_found_error(e):
            if is_quota_error:
                _quota_cooldown_until = time.time() + 600  # 10 minutes
            return _local_ats_fallback(
                resume_text,
                reason="Runtime provider-side error. Local fallback was used."
            )
        
        return {
            "candidate_name": "System Error",
            "overall_score": 0,
            "verdict": "ERROR",
            "track_scores": {
                "product_based": 0,
                "service_based": 0,
                "incubator_startup": 0
            },
            "detailed_analysis": {
                "strengths": [],
                "weaknesses": [f"{error_type}: {str(e)[:150]}"],
                "actionable_improvements": [
                    "Check server logs for detailed error information",
                    "Verify API key is correctly configured",
                    "Ensure network connectivity to Groq API servers"
                ]
            },
            "interview_questions": {
                "technical": "None",
                "behavioral": "None"
            }
        }


def judge_resume(resume_text, track="PRODUCT"):
    """
    Legacy API kept for backwards compatibility.

    IMPORTANT: This now delegates to the entry-level ATS analyzer to avoid
    malformed/truncated JSON issues and to keep behavior consistent.
    """
    ats = analyze_resume_ats(resume_text)

    # Map ATS schema → legacy schema
    overall = ats.get("overall_score", 0)
    verdict = ats.get("verdict", "ERROR")
    legacy_verdict = "REJECTED"
    if verdict == "Shortlist":
        legacy_verdict = "PASS"
    elif verdict == "Borderline":
        legacy_verdict = "REJECTED"
    elif verdict == "Reject":
        legacy_verdict = "REJECTED"
    elif verdict == "ERROR":
        legacy_verdict = "ERROR"

    weaknesses = ats.get("detailed_analysis", {}).get("weaknesses", [])
    improvements = ats.get("detailed_analysis", {}).get("actionable_improvements", [])
    tech_q = ats.get("interview_questions", {}).get("technical", "None")

    return {
        "candidate_name": ats.get("candidate_name", "Unknown"),
        "signal_score": int(overall) if isinstance(overall, int) else 0,
        "verdict": legacy_verdict,
        "red_flags": weaknesses if isinstance(weaknesses, list) else [],
        "brutal_feedback": (improvements[0] if isinstance(improvements, list) and improvements else "No feedback provided"),
        "interview_question": tech_q,
    }


# Test function
if __name__ == "__main__":
    # Test with a deliberately weak resume
    weak_resume = """
    JOHN DOE
    Software Engineer
    Email: john@example.com | Phone: +91-9876543210
    
    SKILLS:
    Programming: Python, JavaScript, HTML, CSS
    Frameworks: React
    Databases: MySQL
    Tools: Git
    
    PROJECTS:
    Todo Application
    - Built a simple todo app using React
    - Users can add and delete tasks
    - Stored data in local storage
    
    Calculator App
    - Created a basic calculator in Python
    - Performs addition, subtraction, multiplication, division
    
    Personal Portfolio Website
    - Made a portfolio website using HTML, CSS, JavaScript
    - Showcases my projects and skills
    
    EDUCATION:
    Bachelor of Technology in Computer Science
    XYZ University, 2020-2024
    CGPA: 7.8/10
    
    ACHIEVEMENTS:
    - Participated in college hackathon
    - Completed online Python course
    """
    
    print("="*60)
    print("TESTING WITH WEAK RESUME")
    print("Expected: Score 30-50, Verdict: REJECTED")
    print("="*60)
    
    result = judge_resume(weak_resume, track="PRODUCT")
    
    print("\n" + "="*60)
    print("TEST RESULT:")
    print("="*60)
    print(json.dumps(result, indent=2))
    
    # Validation
    print("\n" + "="*60)
    print("VALIDATION:")
    print("="*60)
    if result["signal_score"] <= 50:
        print("PASS: Score is appropriately low for weak resume")
    else:
        print(f"WARNING: Score too high ({result['signal_score']}) for weak resume")
    
    if result["verdict"] == "REJECTED":
        print("PASS: Verdict is REJECTED as expected")
    else:
        print(f"WARNING: Should be REJECTED, got {result['verdict']}")
    
    print("\nTest complete!")
