import { useMemo, useState } from 'react'
import './AIInterviewer.css'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000').replace(/\/$/, '')

function AIInterviewer({
  resumeText = '',
  track = 'PRODUCT',
  candidateName = 'Candidate',
}) {
  const [messages, setMessages] = useState([])
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState('')
  const [score, setScore] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const canStart = useMemo(() => resumeText.trim().length > 40, [resumeText])
  const hasStarted = messages.length > 0

  const requestInterviewer = async (nextMessages) => {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE}/ai_interviewer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: resumeText,
          track,
          candidate_name: candidateName,
          messages: nextMessages,
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error || `Interview request failed: ${response.status}`)
      }

      const reply = data.reply || {}
      const interviewerMessage = {
        role: 'interviewer',
        content: reply.message || 'Tell me more about your strongest technical project.',
      }
      setMessages([...nextMessages, interviewerMessage])
      setFeedback(reply.feedback || '')
      setScore(reply.score ?? null)
    } catch (err) {
      console.error(err)
      setError(err.message || 'Failed to contact AI interviewer.')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = () => {
    requestInterviewer([])
  }

  const handleSend = () => {
    const trimmed = answer.trim()
    if (!trimmed) {
      setError('Write an answer before sending it.')
      return
    }

    const nextMessages = [...messages, { role: 'candidate', content: trimmed }]
    setAnswer('')
    requestInterviewer(nextMessages)
  }

  return (
    <section className="interviewer-root">
      <div className="interviewer-header">
        <div>
          <p className="interviewer-kicker">AI Interviewer</p>
          <h2>{track} technical interview</h2>
        </div>
        {score !== null && (
          <div className="interviewer-score">
            <span>{score}</span>
            <small>/100</small>
          </div>
        )}
      </div>

      <div className="interviewer-body">
        {!hasStarted && (
          <div className="interviewer-empty">
            <p>
              Start a resume-aware interview round with adaptive follow-up questions and short feedback after each answer.
            </p>
            <button type="button" onClick={handleStart} disabled={loading || !canStart}>
              {loading ? 'Starting...' : 'Start AI Interview'}
            </button>
          </div>
        )}

        {hasStarted && (
          <>
            <div className="interviewer-transcript" aria-live="polite">
              {messages.map((message, index) => (
                <div className={`interviewer-message ${message.role}`} key={`${message.role}-${index}`}>
                  <span>{message.role === 'candidate' ? 'You' : 'AI Interviewer'}</span>
                  <p>{message.content}</p>
                </div>
              ))}
              {loading && (
                <div className="interviewer-message interviewer">
                  <span>AI Interviewer</span>
                  <p>Thinking...</p>
                </div>
              )}
            </div>

            {feedback && (
              <div className="interviewer-feedback">
                <strong>Feedback</strong>
                <p>{feedback}</p>
              </div>
            )}

            <label className="interviewer-answer">
              Your answer
              <textarea
                rows={6}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Answer with context, technical details, trade-offs, and measurable outcomes..."
                disabled={loading}
              />
            </label>
            <button type="button" onClick={handleSend} disabled={loading || !answer.trim()}>
              {loading ? 'Sending...' : 'Send Answer'}
            </button>
          </>
        )}

        {error && <div className="interviewer-error">{error}</div>}
      </div>
    </section>
  )
}

export default AIInterviewer
