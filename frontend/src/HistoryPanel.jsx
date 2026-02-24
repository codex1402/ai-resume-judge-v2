import { useState } from 'react'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000').replace(/\/$/, '')

function HistoryPanel() {
  const [candidateId, setCandidateId] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [candidateHistory, setCandidateHistory] = useState(null)
  const [sessionHistory, setSessionHistory] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const fetchCandidateHistory = async () => {
    if (!candidateId.trim()) {
      setError('Enter a candidate ID first.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/candidate_history/${candidateId.trim()}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `Failed: ${res.status}`)
      setCandidateHistory(data)
    } catch (err) {
      setError(err.message || 'Failed to fetch candidate history.')
      setCandidateHistory(null)
    } finally {
      setLoading(false)
    }
  }

  const fetchSessionHistory = async () => {
    if (!sessionId.trim()) {
      setError('Enter an assessment session ID first.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/assessment_session/${sessionId.trim()}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `Failed: ${res.status}`)
      setSessionHistory(data)
    } catch (err) {
      setError(err.message || 'Failed to fetch assessment session.')
      setSessionHistory(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="history-panel">
      <div className="history-header">
        <h3>Candidate History</h3>
        <p>Inspect persisted candidate and assessment history from DB.</p>
      </div>

      <div className="history-controls">
        <div className="history-control">
          <label htmlFor="candidate-id">Candidate ID</label>
          <div className="history-input-row">
            <input
              id="candidate-id"
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
              placeholder="e.g. 1"
            />
            <button type="button" onClick={fetchCandidateHistory} disabled={loading}>
              Fetch Candidate
            </button>
          </div>
        </div>

        <div className="history-control">
          <label htmlFor="session-id">Assessment Session ID</label>
          <div className="history-input-row">
            <input
              id="session-id"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              placeholder="e.g. 12"
            />
            <button type="button" onClick={fetchSessionHistory} disabled={loading}>
              Fetch Session
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {candidateHistory && (
        <div className="history-block">
          <h4>Candidate History JSON</h4>
          <pre className="history-json">{JSON.stringify(candidateHistory, null, 2)}</pre>
        </div>
      )}

      {sessionHistory && (
        <div className="history-block">
          <h4>Assessment Session JSON</h4>
          <pre className="history-json">{JSON.stringify(sessionHistory, null, 2)}</pre>
        </div>
      )}
    </section>
  )
}

export default HistoryPanel
