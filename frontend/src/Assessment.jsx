import { useEffect, useMemo, useRef, useState } from 'react'
import './Assessment.css'

const API_BASE = 'http://127.0.0.1:5000'
const TRACK_TIME_LIMITS = {
  PRODUCT: 35 * 60,
  SERVICE: 30 * 60,
  STARTUP: 25 * 60,
}

function formatTime(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60).toString().padStart(2, '0')
  const secs = (totalSeconds % 60).toString().padStart(2, '0')
  return `${mins}:${secs}`
}

function Assessment({ initialResumeText = '', initialTrack = 'PRODUCT' }) {
  const [resumeText, setResumeText] = useState(initialResumeText)
  const [track, setTrack] = useState(initialTrack)
  const [assessment, setAssessment] = useState(null)
  const [mcqAnswers, setMcqAnswers] = useState({})
  const [dynamicAnswers, setDynamicAnswers] = useState({})
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [testMode, setTestMode] = useState(false)
  const [violations, setViolations] = useState(0)
  const [timeLeft, setTimeLeft] = useState(TRACK_TIME_LIMITS[initialTrack] || TRACK_TIME_LIMITS.PRODUCT)
  const startRef = useRef(null)
  const submittedRef = useRef(false)

  const canGenerate = useMemo(
    () => resumeText.trim().length > 40 && ['PRODUCT', 'SERVICE', 'STARTUP'].includes(track),
    [resumeText, track]
  )

  useEffect(() => {
    if (!testMode || result) return
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval)
          handleSubmitAssessment(true)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [testMode, result])

  useEffect(() => {
    if (!testMode || result) return undefined

    const onVisibility = () => {
      if (document.hidden) {
        setViolations((v) => v + 1)
      }
    }
    const onBlur = () => setViolations((v) => v + 1)

    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', onBlur)
    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('blur', onBlur)
    }
  }, [testMode, result])

  const handleGenerate = async () => {
    if (!canGenerate) {
      setError('Please provide resume text and select a valid track.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)
    setAssessment(null)
    setMcqAnswers({})
    setDynamicAnswers({})
    setViolations(0)
    submittedRef.current = false

    try {
      const response = await fetch(`${API_BASE}/generate_assessment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText,
          track,
        }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error || `Request failed: ${response.status}`)
      }

      setAssessment(data)
      setTimeLeft(TRACK_TIME_LIMITS[data.track] || TRACK_TIME_LIMITS.PRODUCT)
      startRef.current = Date.now()
      setTestMode(true)
    } catch (err) {
      console.error(err)
      setError(err.message || 'Failed to generate assessment.')
    } finally {
      setLoading(false)
    }
  }

  const handleMcqChange = (questionId, answer) => {
    setMcqAnswers((prev) => ({ ...prev, [questionId]: answer }))
  }

  const handleDynamicChange = (questionId, value) => {
    setDynamicAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  const handleSubmitAssessment = async (autoSubmitted = false) => {
    if (!assessment || submitting || submittedRef.current) return
    submittedRef.current = true
    setSubmitting(true)
    setError('')

    const elapsed = startRef.current ? Math.floor((Date.now() - startRef.current) / 1000) : 0
    const payload = {
      track: assessment.track,
      resume_text: resumeText,
      mcq_answers: assessment.mcqs.map((q) => ({
        id: q.id,
        selected_answer: mcqAnswers[q.id] || '',
      })),
      subjective_answers: assessment.dynamic_questions.map((q) => ({
        id: q.id,
        question: q.question,
        answer: dynamicAnswers[q.id] || '',
      })),
      violations,
      auto_submitted: autoSubmitted,
      time_taken_sec: elapsed,
    }

    try {
      const response = await fetch(`${API_BASE}/submit_assessment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error || `Submission failed: ${response.status}`)
      }
      setResult(data)
      setTestMode(false)
    } catch (err) {
      submittedRef.current = false
      console.error(err)
      setError(err.message || 'Failed to submit assessment.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="assessment-root">
      {!testMode && (
        <div className="assessment-card">
          <h2>Online Assessment (Proving Grounds)</h2>
          <p>Track-specific exam with timer, proctor checks, and auto-submit.</p>

          <div className="assessment-controls">
            <label>
              Track
              <select value={track} onChange={(e) => setTrack(e.target.value)}>
                <option value="PRODUCT">PRODUCT (Hard DSA + System)</option>
                <option value="SERVICE">SERVICE (Passage + Reasoning + Technical)</option>
                <option value="STARTUP">STARTUP (Practical Build + Deploy)</option>
              </select>
            </label>

            <label>
              Resume Text
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                rows={6}
                placeholder="Paste parsed resume text here..."
              />
            </label>

            <button type="button" onClick={handleGenerate} disabled={loading || !canGenerate}>
              {loading ? 'Generating...' : 'Enter Secure Assessment'}
            </button>
          </div>

          {error && <div className="assessment-error">{error}</div>}
        </div>
      )}

      {testMode && assessment && (
        <div className="secure-assessment">
          <div className="secure-topbar">
            <div>
              <h3>{assessment.track} Assessment</h3>
              <p className="muted">HackerRank-style timed environment</p>
            </div>
            <div className="secure-metrics">
              <span className={`timer-chip ${timeLeft <= 300 ? 'danger' : ''}`}>
                Time Left: {formatTime(timeLeft)}
              </span>
              <span className={`violation-chip ${violations > 0 ? 'warn' : ''}`}>
                Tab Violations: {violations}
              </span>
            </div>
          </div>

          <div className="questions-block">
            <h4>Multiple Choice Questions</h4>
            {assessment.mcqs.map((q) => (
              <div className="question-card" key={q.id}>
                <p className="question-title">{q.id}. [{q.section || 'General'}] {q.question}</p>
                <div className="options-grid">
                  {q.options.map((option) => {
                    const letter = option.split('.')[0].trim()
                    return (
                      <label key={option} className="option-item">
                        <input
                          type="radio"
                          name={`mcq-${q.id}`}
                          value={letter}
                          checked={(mcqAnswers[q.id] || '') === letter}
                          onChange={() => handleMcqChange(q.id, letter)}
                        />
                        <span>{option}</span>
                      </label>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="questions-block">
            <h4>Dynamic Deep-Dive Questions</h4>
            {assessment.dynamic_questions.map((q) => (
              <div className="question-card" key={q.id}>
                <p className="question-title">{q.id}. {q.question}</p>
                <textarea
                  rows={9}
                  className="answer-box"
                  placeholder="Write a structured technical answer..."
                  value={dynamicAnswers[q.id] || ''}
                  onChange={(e) => handleDynamicChange(q.id, e.target.value)}
                />
              </div>
            ))}
          </div>

          <button type="button" className="submit-btn" disabled={submitting} onClick={() => handleSubmitAssessment(false)}>
            {submitting ? 'Submitting...' : 'Submit Assessment'}
          </button>
          {error && <div className="assessment-error">{error}</div>}
        </div>
      )}

      {result && (
        <div className="assessment-card">
          <h3>Assessment Result</h3>
          <p>
            Final Score: <strong>{result.final_score}</strong> | Verdict: <strong>{result.verdict}</strong>
          </p>
          <p className="muted">
            MCQ: {result.breakdown?.mcq_score}/{result.breakdown?.mcq_max} | Subjective: {result.breakdown?.subjective_score}/{result.breakdown?.subjective_max} | Violation Penalty: {result.breakdown?.violation_penalty}
          </p>
          <div className="questions-block">
            <h4>Subjective Feedback</h4>
            {(result.subjective_details || []).map((d) => (
              <div className="question-card" key={d.id}>
                <p className="question-title">Q{d.id}: {d.score}/{d.max_score}</p>
                <p>{d.feedback}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

export default Assessment
