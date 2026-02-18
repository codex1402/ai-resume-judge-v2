import { useState } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setResult(null)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a PDF first!")
      return
    }
    
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://127.0.0.1:5000/analyze', {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }
      
      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error("Error:", error)
      setError("Failed to connect to the ATS Analyzer. Is the backend running?")
    } finally {
      setLoading(false)
    }
  }

  const getVerdictColor = (verdict) => {
    switch(verdict?.toLowerCase()) {
      case 'shortlist':
        return '#4CAF50'
      case 'borderline':
        return '#FF9800'
      case 'reject':
        return '#F44336'
      default:
        return '#757575'
    }
  }

  const getScoreColor = (score) => {
    if (score >= 80) return '#4CAF50'
    if (score >= 70) return '#8BC34A'
    if (score >= 60) return '#FFC107'
    if (score >= 50) return '#FF9800'
    return '#F44336'
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🤖 Entry-Level ATS Resume Analyzer</h1>
        <p>Upload a resume to get a detailed ATS analysis for entry-level software engineering roles</p>
      </header>

      <div className="upload-section">
        <div className="upload-card">
          <input 
            type="file" 
            accept=".pdf" 
            onChange={handleFileChange}
            id="file-input"
            disabled={loading}
          />
          <button 
            onClick={handleUpload} 
            disabled={loading || !file}
            className="upload-button"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Analyzing...
              </>
            ) : (
              <>
                📊 Analyze Resume
              </>
            )}
          </button>
        </div>
        {error && <div className="error-message">{error}</div>}
      </div>

      {result && (
        <div className="dashboard">
          {/* Error Banner for API Quota/Auth Errors */}
          {(result.verdict === 'ERROR' && result.detailed_analysis?.weaknesses?.some(w => 
            w.toLowerCase().includes('quota') || w.toLowerCase().includes('api')
          )) && (
            <div className="error-banner">
              <div className="error-banner-content">
                <span className="error-icon">⚠️</span>
                <div className="error-text">
                  <h3>API Quota Exceeded</h3>
                  <p>Your Google Gemini API quota has been exceeded. Please check your Google Cloud Console or wait for the quota to reset.</p>
                </div>
              </div>
            </div>
          )}
          
          {/* Overall Score & Verdict Section */}
          <div className="score-section">
            <div className="score-card main-score">
              <div className="score-header">
                <h2>{result.candidate_name || 'Unknown Candidate'}</h2>
                <span 
                  className="verdict-badge"
                  style={{ backgroundColor: getVerdictColor(result.verdict) }}
                >
                  {result.verdict || 'N/A'}
                </span>
              </div>
              <div className="score-display">
                <span 
                  className="overall-score"
                  style={{ color: getScoreColor(result.overall_score || 0) }}
                >
                  {result.overall_score || 0}
                </span>
                <span className="score-total">/100</span>
              </div>
              <p className="score-label">Overall ATS Score</p>
            </div>
          </div>

          {/* Track Scores Section */}
          <div className="tracks-section">
            <h3 className="section-title">Track-Specific Scores</h3>
            <div className="tracks-grid">
              <div className="track-card">
                <div className="track-header">
                  <h4>🏢 Product-Based</h4>
                  <span className="track-score">
                    {result.track_scores?.product_based || 0}/100
                  </span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ 
                      width: `${result.track_scores?.product_based || 0}%`,
                      backgroundColor: getScoreColor(result.track_scores?.product_based || 0)
                    }}
                  ></div>
                </div>
                <p className="track-description">
                  DSA, Core CS, Problem Solving, Optimization
                </p>
              </div>

              <div className="track-card">
                <div className="track-header">
                  <h4>💼 Service-Based</h4>
                  <span className="track-score">
                    {result.track_scores?.service_based || 0}/100
                  </span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ 
                      width: `${result.track_scores?.service_based || 0}%`,
                      backgroundColor: getScoreColor(result.track_scores?.service_based || 0)
                    }}
                  ></div>
                </div>
                <p className="track-description">
                  Tech Stack Breadth, Teamwork, Full-Stack Skills
                </p>
              </div>

              <div className="track-card">
                <div className="track-header">
                  <h4>🚀 Incubator/Startup</h4>
                  <span className="track-score">
                    {result.track_scores?.incubator_startup || 0}/100
                  </span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ 
                      width: `${result.track_scores?.incubator_startup || 0}%`,
                      backgroundColor: getScoreColor(result.track_scores?.incubator_startup || 0)
                    }}
                  ></div>
                </div>
                <p className="track-description">
                  Hustle, Deployments, MVP Building, Ownership
                </p>
              </div>
            </div>
          </div>

          {/* Detailed Analysis Section */}
          <div className="analysis-section">
            <h3 className="section-title">Detailed Analysis</h3>
            <div className="analysis-grid">
              {/* Strengths */}
              <div className="analysis-card strengths-card">
                <div className="analysis-header">
                  <h4>✅ Strengths</h4>
                  <span className="count-badge">{result.detailed_analysis?.strengths?.length || 0}</span>
                </div>
                <ul className="analysis-list">
                  {(result.detailed_analysis?.strengths || []).map((strength, idx) => (
                    <li key={idx}>{strength}</li>
                  ))}
                  {(!result.detailed_analysis?.strengths || result.detailed_analysis.strengths.length === 0) && (
                    <li className="empty-state">No strengths identified</li>
                  )}
                </ul>
              </div>

              {/* Weaknesses */}
              <div className="analysis-card weaknesses-card">
                <div className="analysis-header">
                  <h4>⚠️ Weaknesses</h4>
                  <span className="count-badge">{result.detailed_analysis?.weaknesses?.length || 0}</span>
                </div>
                <ul className="analysis-list">
                  {(result.detailed_analysis?.weaknesses || []).map((weakness, idx) => (
                    <li key={idx}>{weakness}</li>
                  ))}
                  {(!result.detailed_analysis?.weaknesses || result.detailed_analysis.weaknesses.length === 0) && (
                    <li className="empty-state">No weaknesses identified</li>
                  )}
                </ul>
              </div>

              {/* Actionable Improvements */}
              <div className="analysis-card improvements-card">
                <div className="analysis-header">
                  <h4>💡 Actionable Improvements</h4>
                  <span className="count-badge">{result.detailed_analysis?.actionable_improvements?.length || 0}</span>
                </div>
                <ul className="analysis-list">
                  {(result.detailed_analysis?.actionable_improvements || []).map((improvement, idx) => (
                    <li key={idx}>{improvement}</li>
                  ))}
                  {(!result.detailed_analysis?.actionable_improvements || result.detailed_analysis.actionable_improvements.length === 0) && (
                    <li className="empty-state">No improvements suggested</li>
                  )}
                </ul>
              </div>
            </div>
          </div>

          {/* Interview Questions Section */}
          <div className="questions-section">
            <h3 className="section-title">Interview Questions</h3>
            <div className="questions-grid">
              <div className="question-card">
                <div className="question-header">
                  <span className="question-icon">💻</span>
                  <h4>Technical Question</h4>
                </div>
                <p className="question-text">
                  {result.interview_questions?.technical || 'No technical question generated'}
                </p>
              </div>

              <div className="question-card">
                <div className="question-header">
                  <span className="question-icon">🤝</span>
                  <h4>Behavioral Question</h4>
                </div>
                <p className="question-text">
                  {result.interview_questions?.behavioral || 'No behavioral question generated'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
