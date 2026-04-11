import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function GuestMode() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { loginAsGuest } = useAuth()
  const navigate = useNavigate()

  const handleGuestLogin = async () => {
    setError('')
    setLoading(true)

    try {
      await loginAsGuest()
      navigate('/')
    } catch (err) {
      setError(err.message || 'Failed to start guest session')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>Play as Guest</h1>
          <p>Jump into the action instantly - no signup required!</p>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        <div className="guest-info">
          <h3>What you can do:</h3>
          <ul>
            <li>Create and join quiz rooms</li>
            <li>Play 1v1 quiz battles</li>
            <li>Compete in real-time</li>
          </ul>

          <h3>Limitations:</h3>
          <ul>
            <li>No game history saved</li>
            <li>No leaderboard access</li>
            <li>Random username assigned</li>
          </ul>
        </div>

        <button 
          onClick={handleGuestLogin}
          className="btn-primary btn-full btn-large"
          disabled={loading}
        >
          {loading ? 'Starting...' : 'Play as Guest'}
        </button>

        <div className="auth-footer">
          <p>Want to save your progress? <a href="/signup">Create an account</a></p>
          <p>Already have an account? <a href="/login">Sign in</a></p>
        </div>
      </div>

      <style jsx>{`
        .guest-info {
          background: var(--surface-color);
          padding: 1.5rem;
          border-radius: var(--radius-md);
          margin: 1.5rem 0;
        }

        .guest-info h3 {
          font-size: 1rem;
          margin-bottom: 0.75rem;
          color: var(--text-primary);
        }

        .guest-info ul {
          list-style: none;
          padding: 0;
          margin: 0 0 1.5rem 0;
        }

        .guest-info ul:last-child {
          margin-bottom: 0;
        }

        .guest-info li {
          padding: 0.5rem 0;
          font-size: 0.95rem;
          color: var(--text-secondary);
        }

        .btn-large {
          padding: 1rem;
          font-size: 1.1rem;
          font-weight: 600;
        }
      `}</style>
    </div>
  )
}

export default GuestMode
