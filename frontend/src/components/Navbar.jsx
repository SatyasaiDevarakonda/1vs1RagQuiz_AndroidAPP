import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useGame } from '../context/GameContext'

function Navbar() {
  const { user, logout } = useAuth()
  const { connected, connectionStatus } = useGame()
  const location = useLocation()
  
  // Theme state - check localStorage for saved preference
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved ? saved === 'dark' : true   // default to dark
  })

  // Apply theme on mount and when changed
  useEffect(() => {
    if (isDark) {
      document.documentElement.setAttribute('data-theme', 'dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.removeAttribute('data-theme')
      localStorage.setItem('theme', 'light')
    }
  }, [isDark])

  const toggleTheme = () => {
    setIsDark(!isDark)
  }

  const handleLogout = () => {
    logout()
  }

  const getStatusClass = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'status-connected'
      case 'connecting':
      case 'reconnecting':
        return 'status-connecting'
      default:
        return 'status-disconnected'
    }
  }

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected'
      case 'connecting':
        return 'Connecting...'
      case 'reconnecting':
        return 'Reconnecting...'
      default:
        return 'Disconnected'
    }
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/" className="brand-link">
          <span className="brand-icon">⚡</span>
          <span className="brand-text">Quiz Battle</span>
        </Link>
      </div>

      <div className="navbar-center">
        <div className={`connection-status ${getStatusClass()}`}>
          <span className="status-dot"></span>
          <span className="status-text">{getStatusText()}</span>
        </div>
        
        {/* Theme Toggle */}
        <button 
          className="theme-toggle" 
          onClick={toggleTheme}
          title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {isDark ? '☀️' : '🌙'}
        </button>
      </div>

      <div className="navbar-actions">
        {user ? (
          <>
            <Link 
              to="/profile" 
              className={`nav-link ${location.pathname === '/profile' ? 'active' : ''}`}
            >
              <span className="nav-icon">👤</span>
              <span className="nav-text">{user.username}</span>
            </Link>
            <button onClick={handleLogout} className="btn-logout">
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="nav-link">Login</Link>
            <Link to="/signup" className="btn-signup">Sign Up</Link>
          </>
        )}
      </div>
    </nav>
  )
}

export default Navbar
