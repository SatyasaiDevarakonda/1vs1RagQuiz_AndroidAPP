import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useGame } from '../context/GameContext'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const {
    connected,
    createRoom,
    joinRoom,
    showToast,
    connectToRoom
  } = useGame()

  const [searchParams, setSearchParams] = useSearchParams()
  const [roomInput, setRoomInput] = useState('')
  const [pdfFile, setPdfFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [gameSettings, setGameSettings] = useState({
    questionsCount: 5,
    timePerQuestion: 15,
    difficulty: 'medium'
  })
  const fileInputRef = useRef(null)

  // Check for room code in URL
  useEffect(() => {
    const roomCode = searchParams.get('room')
    if (roomCode && connected) {
      setRoomInput(roomCode)
      const timer = setTimeout(() => {
        joinRoom(roomCode)
        setSearchParams({})
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [searchParams, connected, joinRoom, setSearchParams])

  const validateAndSetFile = (file) => {
    if (!file) return
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain'
    ]
    if (!validTypes.includes(file.type)) {
      showToast('Please upload a PDF, DOCX, or TXT file', 'error')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast('File size must be less than 10MB', 'error')
      return
    }
    setPdfFile(file)
  }

  const handleFileChange = (e) => {
    validateAndSetFile(e.target.files[0])
    // reset so same file can be re-selected
    e.target.value = ''
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    validateAndSetFile(e.dataTransfer.files[0])
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => setDragOver(false)

  const handleRemoveFile = (e) => {
    e.stopPropagation()
    setPdfFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleCreateRoomWithPDF = async () => {
    if (!pdfFile) {
      showToast('Please upload a PDF file first', 'error')
      return
    }
    if (!connected) {
      showToast('Connecting to server... Please wait', 'warning')
      return
    }

    setUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', pdfFile)
      formData.append('questions_count', gameSettings.questionsCount)
      formData.append('time_per_question', gameSettings.timePerQuestion)
      formData.append('difficulty', gameSettings.difficulty)
      formData.append('mode', 'multiplayer')

      showToast('Uploading PDF and generating questions...', 'info')

      const response = await fetch('/api/rooms/create-with-pdf', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${api.getToken()}`
        },
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create room')
      }

      const data = await response.json()
      showToast(`Room created! ${data.questions_generated} questions generated`, 'success')
      connectToRoom(data.room_code)

    } catch (error) {
      console.error('Error creating room:', error)
      showToast(error.message || 'Failed to create room with PDF', 'error')
    } finally {
      setUploading(false)
    }
  }

  const handleJoinRoom = () => {
    if (!roomInput || roomInput.length !== 4) {
      showToast('Please enter a valid 4-digit room code', 'error')
      return
    }
    joinRoom(roomInput)
  }

  const handleRoomInputChange = (e) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 4)
    setRoomInput(value)
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Welcome, {user?.username}!</h1>
        <p>Upload your study material and battle with AI-generated questions</p>
      </div>

      <div className="game-modes">
        {/* AI-Powered Quiz Mode Card */}
        <div className="mode-card featured ai-mode">
          <div className="mode-badge">🤖 AI-Powered</div>
          <div className="mode-icon">📄</div>
          <h2>Create Quiz from PDF</h2>
          <p>Upload your study material and compete</p>

          <div className="settings-panel">
            {/* PDF Upload Zone */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                style={{ display: 'none' }}
                id="pdf-file-input"
              />

              {!pdfFile ? (
                <label
                  htmlFor="pdf-file-input"
                  className={`pdf-upload-zone ${dragOver ? 'drag-over' : ''}`}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                >
                  <span className="upload-icon">📂</span>
                  <span className="upload-label-text">Click to upload or drag & drop</span>
                  <span className="upload-hint">PDF, DOCX or TXT · Max 10 MB</span>
                </label>
              ) : (
                <div
                  className="pdf-upload-zone has-file"
                  onClick={() => fileInputRef.current?.click()}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="file-selected-info">
                    <div className="file-selected-left">
                      <span className="file-selected-icon">✅</span>
                      <span className="file-selected-name" title={pdfFile.name}>
                        {pdfFile.name}
                      </span>
                    </div>
                    <span className="file-selected-size">{formatFileSize(pdfFile.size)}</span>
                    <button
                      className="file-remove-btn"
                      onClick={handleRemoveFile}
                      title="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                  <span className="upload-hint" style={{ marginTop: '4px' }}>
                    Click to change file
                  </span>
                </div>
              )}
            </div>

            <div className="setting-row">
              <label>Questions</label>
              <select
                value={gameSettings.questionsCount}
                onChange={(e) => setGameSettings(prev => ({
                  ...prev,
                  questionsCount: parseInt(e.target.value)
                }))}
              >
                <option value={5}>5 Questions</option>
                <option value={10}>10 Questions</option>
                <option value={15}>15 Questions</option>
                <option value={20}>20 Questions</option>
              </select>
            </div>

            <div className="setting-row">
              <label>Time per Question</label>
              <select
                value={gameSettings.timePerQuestion}
                onChange={(e) => setGameSettings(prev => ({
                  ...prev,
                  timePerQuestion: parseInt(e.target.value)
                }))}
              >
                <option value={10}>10 seconds</option>
                <option value={15}>15 seconds</option>
                <option value={30}>30 seconds</option>
                <option value={60}>60 seconds</option>
              </select>
            </div>

            <div className="setting-row">
              <label>Difficulty</label>
              <select
                value={gameSettings.difficulty}
                onChange={(e) => setGameSettings(prev => ({
                  ...prev,
                  difficulty: e.target.value
                }))}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <button
            className="btn-mode btn-create btn-ai"
            onClick={handleCreateRoomWithPDF}
            disabled={!connected || !pdfFile || uploading}
          >
            {uploading ? (
              <>
                <span className="btn-spinner" />
                Generating Questions...
              </>
            ) : (
              '🚀 Create AI Quiz Room'
            )}
          </button>

          <div className="ai-info">
            <small>💡 Questions are generated exclusively from your uploaded document</small>
          </div>
        </div>

        {/* Join Room Card */}
        <div className="mode-card">
          <div className="mode-icon">🔗</div>
          <h2>Join Existing Room</h2>
          <p>Enter a room code to join a friend's quiz</p>

          <div className="join-room-section">
            <input
              type="text"
              value={roomInput}
              onChange={handleRoomInputChange}
              placeholder="0000"
              maxLength={4}
              className="room-input-large"
            />
            <button
              className="btn-mode btn-join"
              onClick={handleJoinRoom}
              disabled={!connected || roomInput.length !== 4}
            >
              Join Room
            </button>
          </div>
        </div>
      </div>

      {/* Stats Preview */}
      {!user?.is_guest && (
        <div className="stats-preview">
          <div className="stat-item">
            <span className="stat-value">{user?.games_played || 0}</span>
            <span className="stat-label">Games Played</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{user?.games_won || 0}</span>
            <span className="stat-label">Victories</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{user?.total_score || 0}</span>
            <span className="stat-label">Total Score</span>
          </div>
        </div>
      )}

      {user?.is_guest && (
        <div className="guest-notice">
          🎮 Playing as guest · <a href="/signup">Sign up</a> to save your stats
        </div>
      )}

      {!connected && (
        <div className="connection-warning">
          <span className="warning-icon">⚠️</span>
          <span>Connecting to game server...</span>
        </div>
      )}

      {/* Competition Link */}
      {!user?.is_guest && (
        <div style={{ marginTop: 'var(--space-xl)', textAlign: 'center' }}>
          <button 
            className="btn-secondary"
            onClick={() => navigate('/competition')}
            style={{ 
              padding: '12px 24px',
              fontSize: '1rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            🏆 Enter Competition Arena
          </button>
        </div>
      )}
    </div>
  )
}

export default Dashboard
