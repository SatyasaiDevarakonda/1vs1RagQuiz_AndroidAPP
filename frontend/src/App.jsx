import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import Login from './components/Login'
import Signup from './components/Signup'
import GuestMode from './components/GuestMode'
import Dashboard from './components/Dashboard'
import Game from './components/Game'
import Profile from './components/Profile'
import CompetitionLobby from './components/CompetitionLobby'
import CompetitionRoom from './components/CompetitionRoom'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loader"></div>
        <p>Loading...</p>
      </div>
    )
  }
  
  if (!user) {
    const params = new URLSearchParams(window.location.search)
    const room = params.get('room')
    if (room) {
      return <Navigate to={`/login?room=${room}`} replace />
    }
    return <Navigate to="/login" replace />
  }
  
  return children
}

function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loader"></div>
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="app">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/login" element={
            user ? <Navigate to="/" replace /> : <Login />
          } />
          <Route path="/signup" element={
            user ? <Navigate to="/" replace /> : <Signup />
          } />
          <Route path="/guest" element={
            user ? <Navigate to="/" replace /> : <GuestMode />
          } />
          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/game" element={
            <ProtectedRoute>
              <Game />
            </ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          } />
          <Route path="/competition" element={
            <ProtectedRoute>
              <CompetitionLobby />
            </ProtectedRoute>
          } />
          <Route path="/competition/room/:roomCode" element={
            <ProtectedRoute>
              <CompetitionRoom />
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
