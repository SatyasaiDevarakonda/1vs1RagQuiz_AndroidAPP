import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import socketService from '../services/socket'

function CompetitionRoom() {
  const { roomCode } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  
  const [room, setRoom] = useState(null)
  const [participants, setParticipants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [connected, setConnected] = useState(false)
  const [gameStatus, setGameStatus] = useState('waiting')
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [timeLeft, setTimeLeft] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [answerReveal, setAnswerReveal] = useState(null)
  const [scores, setScores] = useState([])
  const [leaderboard, setLeaderboard] = useState([])
  const [isCreator, setIsCreator] = useState(false)
  
  const timerRef = useRef(null)

  useEffect(() => {
    loadRoom()
    connectWebSocket()
    
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      socketService.off('competition_player_joined')
      socketService.off('competition_started')
      socketService.off('competition_question')
      socketService.off('competition_answer_reveal')
      socketService.off('competition_answer_received')
      socketService.off('competition_finished')
      socketService.off('competition_participant_joined')
    }
  }, [roomCode])

  const loadRoom = async () => {
    try {
      const data = await api.getCompetitionRoom(roomCode)
      setRoom(data.room)
      setParticipants(data.participants || [])
      
      if (data.room.status === 'active') {
        setGameStatus('playing')
      }
      
      // Check if current user is the creator
      if (user && data.room.created_by === user.id) {
        setIsCreator(true)
      }
    } catch (err) {
      setError(err.message || 'Failed to load room')
    } finally {
      setLoading(false)
    }
  }

  const connectWebSocket = async () => {
    try {
      await socketService.connect()
      
      socketService.on('competition_player_joined', (data) => {
        setParticipants(data.participants)
      })
      socketService.on('competition_participant_joined', (data) => {
        setParticipants(data.participants)
      })
      socketService.on('competition_started', (data) => {
        setGameStatus('playing')
      })
      socketService.on('competition_question', (data) => {
        handleNewQuestion(data)
      })
      socketService.on('competition_answer_reveal', (data) => {
        handleAnswerReveal(data)
      })
      socketService.on('competition_answer_received', (data) => {
      })
      socketService.on('competition_finished', (data) => {
        handleGameFinished(data)
      })
      
      socketService.send({
        event: 'join_competition',
        data: { roomCode, role: 'player' }
      })
      
      setConnected(true)
    } catch (err) {
      console.error('WebSocket connection failed:', err)
      setError('Failed to connect to game server')
    }
  }

  const handleNewQuestion = (data) => {
    setCurrentQuestion({
      questionIndex: data.question_index,
      totalQuestions: data.total_questions,
      question: data.question,
      options: data.options,
      timePerQuestion: data.time_per_question,
      endTime: data.end_time
    })
    setSelectedAnswer(null)
    setAnswerReveal(null)
    setTimeLeft(data.time_per_question)
    
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }

  const handleAnswerReveal = (data) => {
    setAnswerReveal({
      questionIndex: data.question_index,
      question: data.question,
      options: data.options,
      correctIndex: data.correct_index,
      explanation: data.explanation,
      scores: data.scores
    })
    setScores(data.scores || [])
  }

  const handleGameFinished = (data) => {
    setGameStatus('finished')
    setLeaderboard(data.leaderboard || [])
    setCurrentQuestion(null)
    if (timerRef.current) clearInterval(timerRef.current)
  }

  const handleSubmitAnswer = (index) => {
    if (selectedAnswer !== null || !currentQuestion) return
    
    setSelectedAnswer(index)
    
    socketService.send({
      event: 'competition_answer',
      data: {
        roomCode,
        answerIndex: index,
        questionIndex: currentQuestion.questionIndex
      }
    })
  }

  const handleStartCompetition = async () => {
    try {
      socketService.send({
        event: 'start_competition',
        data: { roomCode }
      })
    } catch (err) {
      setError(err.message || 'Failed to start competition')
    }
  }

  const handleLeaveRoom = () => {
    socketService.send({
      event: 'leave_competition',
      data: { roomCode }
    })
    navigate('/competition')
  }

  if (loading) {
    return (
      <div className="competition-room loading-screen">
        <div className="loader"></div>
        <p>Loading competition...</p>
      </div>
    )
  }

  if (error && !room) {
    return (
      <div className="competition-room error-screen">
        <p>{error}</p>
        <button onClick={() => navigate('/competition')}>Back to Lobby</button>
      </div>
    )
  }

  if (gameStatus === 'finished' && leaderboard.length > 0) {
    return (
      <div className="competition-room finished-screen">
        <h1>🏆 Competition Results</h1>
        
        <div className="winner-announcement">
          <div className="trophy">🏆</div>
          <h2>Winner: {leaderboard[0]?.display_name}</h2>
          <p className="winner-score">{leaderboard[0]?.score} points</p>
        </div>

        <div className="final-leaderboard">
          <h3>Final Standings</h3>
          {leaderboard.map((entry, idx) => (
            <div 
              key={entry.student_id} 
              className={`leaderboard-entry ${entry.student_id === user?.id ? 'you' : ''} ${idx === 0 ? 'winner' : ''}`}
            >
              <span className="rank">{idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `#${idx + 1}`}</span>
              <span className="name">
                {entry.display_name}
                {entry.student_id === user?.id && ' (You)'}
              </span>
              <span className="score">{entry.score} pts</span>
              <span className="accuracy">{entry.accuracy}% accuracy</span>
            </div>
          ))}
        </div>

        <div className="actions">
          <button className="btn-primary" onClick={() => navigate('/competition')}>
            Back to Lobby
          </button>
        </div>
      </div>
    )
  }

  if (gameStatus === 'playing' && currentQuestion) {
    const timePerQuestion = currentQuestion.timePerQuestion || 15
    const timerPercent = (timeLeft / timePerQuestion) * 100

    return (
      <div className="competition-room playing-screen">
        <div className="game-header">
          <div className="progress-info">
            <span>Question {currentQuestion.questionIndex + 1} of {currentQuestion.totalQuestions}</span>
          </div>
          <div className="timer-bar">
            <div className="timer-fill" style={{ width: `${timerPercent}%` }} />
          </div>
          <div className="timer-text">{timeLeft}s</div>
        </div>

        <div className="live-scores">
          {scores.slice(0, 5).map((s) => (
            <div key={s.student_id} className={`score-entry ${s.student_id === user?.id ? 'you' : ''}`}>
              <span className="name">{s.display_name}</span>
              <span className="score">{s.score}</span>
            </div>
          ))}
        </div>

        {answerReveal ? (
          <div className="answer-reveal">
            <h2>{answerReveal.question}</h2>
            <div className="options-grid">
              {answerReveal.options.map((option, idx) => (
                <div
                  key={idx}
                  className={`option ${
                    idx === answerReveal.correctIndex ? 'correct' : ''
                  } ${idx === selectedAnswer && idx !== answerReveal.correctIndex ? 'wrong' : ''}`}
                >
                  <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                  <span className="option-text">{option}</span>
                </div>
              ))}
            </div>
            {answerReveal.explanation && (
              <div className="explanation">
                <strong>Explanation:</strong> {answerReveal.explanation}
              </div>
            )}
          </div>
        ) : (
          <div className="question-container">
            <h2 className="question-text">{currentQuestion.question}</h2>
            <div className="options-grid">
              {currentQuestion.options.map((option, idx) => (
                <button
                  key={idx}
                  className={`option-btn ${selectedAnswer === idx ? 'selected' : ''}`}
                  onClick={() => handleSubmitAnswer(idx)}
                  disabled={selectedAnswer !== null}
                >
                  <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                  <span className="option-text">{option}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="competition-room waiting-screen">
      <div className="room-info">
        <h1>Competition Room</h1>
        <div className="room-code-display">
          <span className="label">Room Code</span>
          <span className="code">{roomCode}</span>
        </div>
      </div>

      <div className="session-info">
        <h2>{room?.session_title || 'Quiz Competition'}</h2>
        <p>{room?.course_name}</p>
        <div className="game-settings">
          <span>❓ {room?.total_questions} Questions</span>
          <span>⏱️ {room?.time_per_question}s per question</span>
        </div>
      </div>

      <div className="participants-list">
        <h3>Players ({participants.length})</h3>
        {participants.map((p) => (
          <div key={p.student_id} className={`participant ${p.student_id === user?.id ? 'you' : ''}`}>
            <span className="name">
              {p.display_name}
              {p.student_id === user?.id && ' (You)'}
            </span>
            <span className="role">{p.role}</span>
            <span className="score">{p.score} pts</span>
          </div>
        ))}
      </div>

      {isCreator && participants.length >= 1 && (
        <button className="btn-start" onClick={handleStartCompetition}>
          Start Competition
        </button>
      )}

      <button className="btn-leave" onClick={handleLeaveRoom}>
        Leave Room
      </button>
    </div>
  )
}

export default CompetitionRoom