import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

function CompetitionLobby() {
  const navigate = useNavigate()
  const [rooms, setRooms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [joinCode, setJoinCode] = useState('')
  const [joining, setJoining] = useState(false)

  useEffect(() => {
    loadActiveRooms()
  }, [])

  const loadActiveRooms = async () => {
    try {
      setLoading(true)
      const data = await api.getActiveCompetitionRooms()
      setRooms(data.rooms || [])
    } catch (err) {
      console.error('Error loading rooms:', err)
      setError('Failed to load competition rooms')
    } finally {
      setLoading(false)
    }
  }

  const handleJoinRoom = async (roomCode) => {
    try {
      setJoining(true)
      await api.joinCompetitionRoom(roomCode)
      navigate(`/competition/room/${roomCode}`)
    } catch (err) {
      setError(err.message || 'Failed to join room')
    } finally {
      setJoining(false)
    }
  }

  const handleJoinByCode = async (e) => {
    e.preventDefault()
    if (!joinCode.trim()) return
    await handleJoinRoom(joinCode.trim().toUpperCase())
  }

  return (
    <div className="competition-lobby">
      <div className="lobby-header">
        <h1>Competition Arena</h1>
        <p>Join a live quiz competition against other players!</p>
      </div>

      <div className="join-by-code">
        <form onSubmit={handleJoinByCode}>
          <input
            type="text"
            placeholder="Enter room code (e.g., CAB12D)"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            maxLength={6}
          />
          <button type="submit" disabled={joining || !joinCode.trim()}>
            {joining ? 'Joining...' : 'Join Room'}
          </button>
        </form>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="active-rooms">
        <h2>Active Competitions</h2>
        
        {loading ? (
          <div className="loading">Loading rooms...</div>
        ) : rooms.length === 0 ? (
          <div className="no-rooms">
            <p>No active competitions available.</p>
            <p>Create a new competition from your session dashboard!</p>
          </div>
        ) : (
          <div className="rooms-grid">
            {rooms.map((room) => (
              <div key={room.id} className="competition-card">
                <div className="card-header">
                  <span className={`status ${room.status}`}>{room.status}</span>
                  <span className="room-code">{room.room_code}</span>
                </div>
                <div className="card-body">
                  <h3>{room.session_title || 'Quiz Competition'}</h3>
                  <p className="course-name">{room.course_name}</p>
                  <div className="card-details">
                    <span>👥 {room.player_count} players</span>
                    <span>❓ {room.total_questions} questions</span>
                    <span>⏱️ {room.time_per_question}s per question</span>
                  </div>
                </div>
                <div className="card-footer">
                  <span className="creator">Created by {room.creator_name}</span>
                  <button 
                    onClick={() => handleJoinRoom(room.room_code)}
                    disabled={joining || room.status !== 'waiting'}
                  >
                    {room.status === 'waiting' ? 'Join' : 'Spectate'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="how-it-works">
        <h2>How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-icon">1</div>
            <h3>Join a Room</h3>
            <p>Find an active competition or enter a room code to join</p>
          </div>
          <div className="step">
            <div className="step-icon">2</div>
            <h3>Answer Questions</h3>
            <p>Answer MCQ questions as fast as you can for maximum points</p>
          </div>
          <div className="step">
            <div className="step-icon">3</div>
            <h3>Climb the Leaderboard</h3>
            <p>Compete to be the top scorer and win the competition!</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CompetitionLobby