import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const { login, loginAsGuest } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const roomCode = searchParams.get('room')

  useEffect(() => {
    if (roomCode) {
      setError(`Please login to join room ${roomCode}`)
    }
  }, [roomCode])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      
      if (roomCode) {
        navigate(`/?room=${roomCode}`)
      } else {
        navigate('/')
      }
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGuestLogin = async () => {
    setError('')
    setLoading(true)

    try {
      await loginAsGuest()
      
      if (roomCode) {
        navigate(`/?room=${roomCode}`)
      } else {
        navigate('/')
      }
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
          <h1>Welcome Back</h1>
          <p>Sign in to continue your quiz battles</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className={`alert ${roomCode ? 'alert-info' : 'alert-error'}`}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              autoComplete="current-password"
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary btn-full"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="divider">
          <span>OR</span>
        </div>

        <button 
          onClick={handleGuestLogin}
          className="btn-secondary btn-full"
          disabled={loading}
        >
          Play as Guest
        </button>

        <div className="auth-footer">
          <p>Don't have an account? <Link to={roomCode ? `/signup?room=${roomCode}` : '/signup'}>Create one</Link></p>
        </div>
      </div>

      <style jsx>{`
        .divider {
          display: flex;
          align-items: center;
          text-align: center;
          margin: 1.5rem 0;
          color: var(--text-tertiary);
          font-size: 0.875rem;
        }

        .divider::before,
        .divider::after {
          content: '';
          flex: 1;
          border-bottom: 1px solid var(--border-color);
        }

        .divider:not(:empty)::before {
          margin-right: 1rem;
        }

        .divider:not(:empty)::after {
          margin-left: 1rem;
        }

        .btn-secondary {
          background: transparent;
          border: 2px solid var(--primary-color);
          color: var(--primary-color);
        }

        .btn-secondary:hover:not(:disabled) {
          background: var(--primary-color);
          color: white;
        }
      `}</style>
    </div>
  )
}

export default Login
