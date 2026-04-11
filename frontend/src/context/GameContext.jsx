import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { socketService } from '../services/socket'

const GameContext = createContext(null)

export function GameProvider({ children }) {
  const navigate = useNavigate()

  // Connection state
  const [connected, setConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState('disconnected')

  // Game state
  const [gameStatus, setGameStatus] = useState('idle')
  const [mode, setMode] = useState(null)
  const [roomCode, setRoomCode] = useState('')
  const [players, setPlayers] = useState([])
  const [settings, setSettings] = useState({ questionsCount: 5, timePerQuestion: 15 })

  // Question state
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [totalQuestions, setTotalQuestions] = useState(0)
  const [timeLeft, setTimeLeft] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [answerResult, setAnswerResult] = useState(null)

  // Results
  const [gameResults, setGameResults] = useState(null)
  const [countdown, setCountdown] = useState(null)

  // UI state
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)

  // Connect WebSocket on mount
  useEffect(() => {
    const initConnection = async () => {
      try {
        console.log('Attempting WebSocket connection...')
        await socketService.connect()
        console.log('WebSocket connected successfully')
      } catch (err) {
        console.error('WebSocket connection failed:', err)
        setError('Failed to connect to game server. Please refresh the page.')
      }
    }

    initConnection()
  }, [])

  // Register socket event handlers
  useEffect(() => {
    const handlers = []

    // Connection status handler
    handlers.push(
      socketService.on('connectionChange', ({ status, socketId }) => {
        console.log('Connection status changed:', status)
        setConnectionStatus(status)
        setConnected(status === 'connected')
      })
    )

    // Room created
    handlers.push(
      socketService.on('room_created', (data) => {
        console.log('Room created:', data)
        setRoomCode(data.roomCode)
        setMode(data.mode)
        setSettings(data.settings)
        setPlayers(data.players || [])
        setGameStatus('waiting')
        navigate('/game')
      })
    )

    // Room joined
    handlers.push(
      socketService.on('room_joined', (data) => {
        console.log('Room joined:', data)
        setRoomCode(data.roomCode)
        setMode(data.mode)
        setSettings(data.settings)
        setPlayers(data.players || [])
        setGameStatus('waiting')
        navigate('/game')
      })
    )

    // Player joined
    handlers.push(
      socketService.on('player_joined', (data) => {
        setPlayers(data.players || [])
      })
    )

    // Player ready changed
    handlers.push(
      socketService.on('player_ready_changed', (data) => {
        setPlayers(data.players || [])
      })
    )

    // Player disconnected
    handlers.push(
      socketService.on('player_disconnected', (data) => {
        setPlayers(data.players || [])
        showToast('A player disconnected', 'warning')
      })
    )

    // Countdown started
    handlers.push(
      socketService.on('countdown_started', (data) => {
        setGameStatus('countdown')
        setCountdown(data.countdown)
      })
    )

    // Countdown tick
    handlers.push(
      socketService.on('countdown_tick', (data) => {
        setCountdown(data.countdown)
      })
    )

    // Game started
    handlers.push(
      socketService.on('game_started', (data) => {
        console.log('Game started:', data)
        setGameStatus('playing')
        setTotalQuestions(data.totalQuestions)
        setCountdown(null)
        setGameResults(null)
        setSettings(prev => ({ ...prev, timePerQuestion: data.timePerQuestion }))
      })
    )

    // New question received — reset all question state
    handlers.push(
      socketService.on('question', (data) => {
        console.log('Question received:', data.questionIndex + 1)
        setCurrentQuestion({
          question: data.question,
          options: data.options,
          category: data.category
        })
        setQuestionIndex(data.questionIndex)
        setTotalQuestions(data.totalQuestions)
        setTimeLeft(data.timeLimit)
        setSelectedAnswer(null)
        setAnswerResult(null)
      })
    )

    // Server time update — just update the timer display
    handlers.push(
      socketService.on('time_update', (data) => {
        setTimeLeft(data.timeLeft)
      })
    )

    // Answer accepted — server confirms our answer was recorded (no correct answer yet)
    handlers.push(
      socketService.on('answer_accepted', (data) => {
        console.log('Answer accepted:', data.answer)
        // selectedAnswer is already set from the click handler,
        // this is just a server confirmation
      })
    )

    // Answer result — server reveals correct answer AFTER timer ends
    // This is the ONLY place where correct/incorrect is shown
    handlers.push(
      socketService.on('answer_result', (data) => {
        console.log('Answer result revealed:', data)
        setAnswerResult({
          correct: data.correct,
          correctAnswer: data.correctAnswer,
          yourAnswer: data.yourAnswer,
          pointsEarned: data.pointsEarned,
          timedOut: data.timedOut
        })
      })
    )

    // Scores update — update both players' scores in real time
    handlers.push(
      socketService.on('scores_update', (data) => {
        setPlayers(data.players || [])
      })
    )

    // Game ended — show final results
    handlers.push(
      socketService.on('game_ended', (data) => {
        console.log('Game ended:', data)
        setGameStatus('finished')
        setGameResults({
          players: data.players,
          winner: data.winner,
          totalQuestions: data.totalQuestions,
          mode: data.mode
        })
        setCurrentQuestion(null)
        setAnswerResult(null)
      })
    )

    // Error
    handlers.push(
      socketService.on('error', (data) => {
        console.error('Server error:', data)
        showToast(data.message || 'An error occurred', 'error')
        setError(data.message)
      })
    )

    // Cleanup handlers on unmount
    return () => {
      handlers.forEach(unsubscribe => unsubscribe())
    }
  }, [navigate])

  // Game actions
  const createRoom = useCallback((gameMode, gameSettings) => {
    if (!connected) {
      showToast('Not connected to server. Please wait...', 'error')
      return
    }

    const token = localStorage.getItem('token')
    socketService.send('create_room', {
      token,
      mode: gameMode,
      settings: gameSettings
    })
  }, [connected])

  const joinRoom = useCallback((code) => {
    if (!connected) {
      showToast('Not connected to server. Please wait...', 'error')
      return
    }

    const token = localStorage.getItem('token')
    socketService.send('join_room', {
      token,
      roomCode: code
    })
  }, [connected])

  const connectToRoom = useCallback((code) => {
    if (!connected) {
      showToast('Waiting for connection...', 'warning')
      setTimeout(() => {
        if (socketService.isConnected()) {
          joinRoom(code)
        }
      }, 1000)
      return
    }
    joinRoom(code)
  }, [connected, joinRoom])

  const toggleReady = useCallback(() => {
    if (!connected) {
      showToast('Not connected to server', 'error')
      return
    }

    socketService.send('toggle_ready', { roomCode })
  }, [connected, roomCode])

  const submitAnswer = useCallback((answer) => {
    if (selectedAnswer || answerResult) {
      return // Already answered or results showing
    }

    if (!connected) {
      showToast('Not connected to server', 'error')
      return
    }

    // Highlight the selected answer immediately
    setSelectedAnswer(answer)
    socketService.send('submit_answer', {
      roomCode,
      answer
    })
  }, [connected, roomCode, selectedAnswer, answerResult])

  const resetGame = useCallback(() => {
    setGameStatus('idle')
    setMode(null)
    setRoomCode('')
    setPlayers([])
    setCurrentQuestion(null)
    setQuestionIndex(0)
    setTotalQuestions(0)
    setTimeLeft(0)
    setSelectedAnswer(null)
    setAnswerResult(null)
    setGameResults(null)
    setCountdown(null)
    setError(null)
    navigate('/')
  }, [navigate])

  // Toast helper
  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }, [])

  const clearToast = useCallback(() => setToast(null), [])

  const value = {
    // Connection
    connected,
    connectionStatus,

    // Game state
    gameStatus,
    mode,
    roomCode,
    players,
    settings,

    // Question
    currentQuestion,
    questionIndex,
    totalQuestions,
    timeLeft,
    selectedAnswer,
    answerResult,

    // Results
    gameResults,
    countdown,

    // UI
    error,
    toast,

    // Actions
    createRoom,
    joinRoom,
    connectToRoom,
    toggleReady,
    submitAnswer,
    resetGame,
    showToast,
    clearToast,
    setSettings
  }

  return (
    <GameContext.Provider value={value}>
      {children}
    </GameContext.Provider>
  )
}

export function useGame() {
  const context = useContext(GameContext)
  if (!context) {
    throw new Error('useGame must be used within a GameProvider')
  }
  return context
}

export default GameContext
