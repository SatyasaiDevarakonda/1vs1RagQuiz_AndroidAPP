import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

function Profile() {
  const { user, updateUser } = useAuth()
  
  // Edit states
  const [isEditingUsername, setIsEditingUsername] = useState(false)
  const [isEditingEmail, setIsEditingEmail] = useState(false)
  const [isEditingPassword, setIsEditingPassword] = useState(false)
  
  // Form values
  const [username, setUsername] = useState(user?.username || '')
  const [newEmail, setNewEmail] = useState('')
  const [emailPassword, setEmailPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  // UI states
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(true)

  useEffect(() => {
    loadGameHistory()
  }, [])

  const loadGameHistory = async () => {
    try {
      const data = await api.getGameHistory()
      setHistory(data.history || [])
    } catch (err) {
      console.error('Failed to load history:', err)
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleUpdateUsername = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const data = await api.updateProfile({ username })
      updateUser(data.user)
      setSuccess('Username updated successfully!')
      setIsEditingUsername(false)
    } catch (err) {
      setError(err.message || 'Failed to update username')
    } finally {
      setLoading(false)
    }
  }

  const handleChangeEmail = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const data = await api.changeEmail(newEmail, emailPassword)
      updateUser(data.user)
      setSuccess('Email changed successfully!')
      setIsEditingEmail(false)
      setNewEmail('')
      setEmailPassword('')
    } catch (err) {
      setError(err.message || 'Failed to change email')
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)

    try {
      await api.changePassword(currentPassword, newPassword)
      setSuccess('Password changed successfully!')
      setIsEditingPassword(false)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err.message || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  const cancelEdit = () => {
    setIsEditingUsername(false)
    setIsEditingEmail(false)
    setIsEditingPassword(false)
    setUsername(user?.username || '')
    setNewEmail('')
    setEmailPassword('')
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setError('')
    setSuccess('')
  }

  const winRate = user?.games_played > 0 
    ? Math.round((user.games_won / user.games_played) * 100) 
    : 0

  const avgScore = user?.games_played > 0
    ? Math.round(user.total_score / user.games_played)
    : 0

  return (
    <div className="profile-page">
      <div className="profile-container">
        {/* Profile Header */}
        <div className="profile-header">
          <div className="profile-avatar">
            <span className="avatar-initial">{user?.username?.charAt(0).toUpperCase()}</span>
          </div>
          <div className="profile-info">
            <h1>{user?.username}</h1>
            <p className="profile-email">{user?.email}</p>
            <p className="profile-joined">
              Member since {new Date(user?.created_at).toLocaleDateString('en-US', { 
                month: 'long', 
                year: 'numeric' 
              })}
            </p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-icon">🎮</span>
            <div className="stat-content">
              <span className="stat-number">{user?.games_played || 0}</span>
              <span className="stat-label">Games Played</span>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-icon">🏆</span>
            <div className="stat-content">
              <span className="stat-number">{user?.games_won || 0}</span>
              <span className="stat-label">Victories</span>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-icon">📊</span>
            <div className="stat-content">
              <span className="stat-number">{winRate}%</span>
              <span className="stat-label">Win Rate</span>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-icon">⭐</span>
            <div className="stat-content">
              <span className="stat-number">{user?.total_score || 0}</span>
              <span className="stat-label">Total Score</span>
            </div>
          </div>
        </div>

        {/* Messages */}
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {/* Account Settings */}
        <div className="settings-section">
          <h2>Account Settings</h2>

          {/* Username */}
          <div className="setting-item">
            <div className="setting-header">
              <div className="setting-info">
                <span className="setting-label">Username</span>
                <span className="setting-value">{user?.username}</span>
              </div>
              {!isEditingUsername && (
                <button 
                  className="btn-edit"
                  onClick={() => setIsEditingUsername(true)}
                >
                  Edit
                </button>
              )}
            </div>
            {isEditingUsername && (
              <form onSubmit={handleUpdateUsername} className="edit-form">
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="New username"
                  minLength={3}
                  maxLength={20}
                  required
                />
                <div className="form-actions">
                  <button type="button" className="btn-cancel" onClick={cancelEdit}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-save" disabled={loading}>
                    {loading ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Email */}
          <div className="setting-item">
            <div className="setting-header">
              <div className="setting-info">
                <span className="setting-label">Email</span>
                <span className="setting-value">{user?.email}</span>
              </div>
              {!isEditingEmail && (
                <button 
                  className="btn-edit"
                  onClick={() => setIsEditingEmail(true)}
                >
                  Change
                </button>
              )}
            </div>
            {isEditingEmail && (
              <form onSubmit={handleChangeEmail} className="edit-form">
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="New email address"
                  required
                />
                <input
                  type="password"
                  value={emailPassword}
                  onChange={(e) => setEmailPassword(e.target.value)}
                  placeholder="Current password"
                  required
                />
                <div className="form-actions">
                  <button type="button" className="btn-cancel" onClick={cancelEdit}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-save" disabled={loading}>
                    {loading ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Password */}
          <div className="setting-item">
            <div className="setting-header">
              <div className="setting-info">
                <span className="setting-label">Password</span>
                <span className="setting-value">••••••••</span>
              </div>
              {!isEditingPassword && (
                <button 
                  className="btn-edit"
                  onClick={() => setIsEditingPassword(true)}
                >
                  Change
                </button>
              )}
            </div>
            {isEditingPassword && (
              <form onSubmit={handleChangePassword} className="edit-form">
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Current password"
                  required
                />
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password"
                  minLength={6}
                  required
                />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  required
                />
                <div className="form-actions">
                  <button type="button" className="btn-cancel" onClick={cancelEdit}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-save" disabled={loading}>
                    {loading ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

        {/* Game History */}
        <div className="history-section">
          <h2>Recent Games</h2>
          {loadingHistory ? (
            <div className="loading-state">
              <div className="loader-small"></div>
              <span>Loading history...</span>
            </div>
          ) : history.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">🎮</span>
              <p>No games played yet</p>
              <p className="empty-hint">Start a quiz to see your history here</p>
            </div>
          ) : (
            <div className="history-list">
              {history.map((game, idx) => (
                <div key={idx} className={`history-item ${game.result}`}>
                  <div className="history-result">
                    {game.result === 'win' && '🏆'}
                    {game.result === 'loss' && '😢'}
                    {game.result === 'draw' && '🤝'}
                    {game.result === 'completed' && '✓'}
                  </div>
                  <div className="history-details">
                    <div className="history-main">
                      <span className="history-mode">
                        {game.mode === 'single' ? 'Solo' : '1v1 Battle'}
                      </span>
                      {game.opponentUsername && (
                        <span className="history-opponent">
                          vs {game.opponentUsername}
                        </span>
                      )}
                    </div>
                    <div className="history-stats">
                      <span>{game.score} pts</span>
                      <span>•</span>
                      <span>{game.correctAnswers}/{game.totalQuestions} correct</span>
                    </div>
                  </div>
                  <div className="history-date">
                    {new Date(game.playedAt).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric'
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Profile
