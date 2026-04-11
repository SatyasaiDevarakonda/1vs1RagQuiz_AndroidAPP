import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGame } from '../context/GameContext'
import { useAuth } from '../context/AuthContext'

function Game() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const {
    gameStatus,
    mode,
    roomCode,
    players,
    settings,
    currentQuestion,
    questionIndex,
    totalQuestions,
    timeLeft,
    selectedAnswer,
    answerResult,
    gameResults,
    countdown,
    toggleReady,
    submitAnswer,
    resetGame,
    connected
  } = useGame()

  const [copied, setCopied] = useState(false)

  // Redirect if no room
  useEffect(() => {
    if (gameStatus === 'idle' && !roomCode) {
      navigate('/')
    }
  }, [gameStatus, roomCode, navigate])

  const copyInviteLink = () => {
    const link = `${window.location.origin}/?room=${roomCode}`
    navigator.clipboard.writeText(link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const currentPlayer = players.find(p => p.username === user?.username)
  const opponent = players.find(p => p.username !== user?.username)

  // Waiting Room View
  if (gameStatus === 'waiting') {
    return (
      <div className="game-screen waiting-screen">
        <div className="waiting-container">
          <h1>Waiting Room</h1>
          
          <div className="room-info">
            <span className="room-label">Room Code</span>
            <span className="room-code">{roomCode}</span>
          </div>

          {mode === 'multiplayer' && (
            <div className="invite-section">
              <button 
                className={`btn-copy ${copied ? 'copied' : ''}`}
                onClick={copyInviteLink}
              >
                {copied ? '✓ Link Copied!' : '📋 Copy Invite Link'}
              </button>
            </div>
          )}

          <div className="players-list">
            <h3>Players ({players.length}/{mode === 'single' ? 1 : 2})</h3>
            {players.map((player, idx) => (
              <div key={idx} className={`player-card ${player.isReady ? 'ready' : ''}`}>
                <div className="player-info">
                  <span className="player-name">
                    {player.username}
                    {player.username === user?.username && ' (You)'}
                  </span>
                </div>
                <span className={`ready-status ${player.isReady ? 'ready' : ''}`}>
                  {player.isReady ? '✓ Ready' : 'Not Ready'}
                </span>
              </div>
            ))}

            {players.length < 2 && mode === 'multiplayer' && (
              <div className="player-card empty">
                <span className="waiting-text">Waiting for opponent...</span>
              </div>
            )}
          </div>

          {mode === 'multiplayer' && players.length === 2 && (
            <button
              className={`btn-ready ${currentPlayer?.isReady ? 'ready' : ''}`}
              onClick={toggleReady}
            >
              {currentPlayer?.isReady ? 'Not Ready' : "I'm Ready!"}
            </button>
          )}

          <button className="btn-cancel" onClick={resetGame}>
            Leave Room
          </button>
        </div>
      </div>
    )
  }

  // Countdown View
  if (gameStatus === 'countdown') {
    return (
      <div className="game-screen countdown-screen">
        <div className="countdown-container">
          <h2>Get Ready!</h2>
          <div className="countdown-number">{countdown}</div>
        </div>
      </div>
    )
  }

  // Playing View
  if (gameStatus === 'playing' && currentQuestion) {
    const timePerQuestion = settings?.timePerQuestion || 15
    const timerPercent = (timeLeft / timePerQuestion) * 100

    return (
      <div className="game-screen playing-screen">
        <div className="game-header">
          <div className="progress-info">
            <span>Question {questionIndex + 1} of {totalQuestions}</span>
            <span className="category">{currentQuestion.category}</span>
          </div>

          <div className="timer-bar">
            <div 
              className="timer-fill" 
              style={{ width: `${timerPercent}%` }}
            />
          </div>
          <div className="timer-text">{timeLeft}s</div>
        </div>

        {/* Scoreboard for multiplayer */}
        {mode === 'multiplayer' && (
          <div className="scoreboard">
            <div className={`score-player ${!opponent ? 'leading' : currentPlayer?.score >= opponent?.score ? 'leading' : ''}`}>
              <span className="score-name">{currentPlayer?.username}</span>
              <span className="score-value">{currentPlayer?.score || 0}</span>
            </div>
            <div className="score-vs">VS</div>
            <div className={`score-player ${opponent && opponent.score > (currentPlayer?.score || 0) ? 'leading' : ''}`}>
              <span className="score-name">{opponent?.username || 'Opponent'}</span>
              <span className="score-value">{opponent?.score || 0}</span>
            </div>
          </div>
        )}

        {/* Solo score display */}
        {mode === 'single' && (
          <div className="solo-score">
            <span className="score-label">Score</span>
            <span className="score-value">{currentPlayer?.score || 0}</span>
          </div>
        )}

        <div className="question-container">
          <h2 className="question-text">{currentQuestion.question}</h2>

          <div className="options-grid">
            {currentQuestion.options.map((option, idx) => {
              let optionClass = 'option-btn'
              
              if (selectedAnswer === option) {
                optionClass += ' selected'
              }
              
              if (answerResult) {
                if (option === answerResult.correctAnswer) {
                  optionClass += ' correct'
                } else if (option === selectedAnswer && !answerResult.correct) {
                  optionClass += ' incorrect'
                }
              }

              return (
                <button
                  key={idx}
                  className={optionClass}
                  onClick={() => submitAnswer(option)}
                  disabled={!!selectedAnswer || !!answerResult}
                >
                  <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                  <span className="option-text">{option}</span>
                </button>
              )
            })}
          </div>

          {answerResult && (
            <div className={`result-message ${answerResult.correct ? 'correct' : 'incorrect'}`}>
              {answerResult.timedOut ? (
                "⏱️ Time's up!"
              ) : answerResult.correct ? (
                <>
                  ✓ Correct! +{answerResult.pointsEarned} pts
                  {answerResult.timeTaken && (
                    <span className="time-bonus"> ({answerResult.timeTaken}s)</span>
                  )}
                </>
              ) : (
                '✗ Wrong!'
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  // Results View
  if (gameStatus === 'finished' && gameResults) {
    const winner = gameResults.winner
    const isWinner = winner === user?.username
    const isDraw = winner === 'draw'

    return (
      <div className="game-screen results-screen">
        <div className="results-container">
          <div className="results-header">
            {mode === 'single' ? (
              <>
                <div className="trophy-icon">🏆</div>
                <h1>Quiz Complete!</h1>
              </>
            ) : isDraw ? (
              <>
                <div className="trophy-icon">🤝</div>
                <h1>It's a Draw!</h1>
              </>
            ) : isWinner ? (
              <>
                <div className="trophy-icon">🏆</div>
                <h1>Victory!</h1>
              </>
            ) : (
              <>
                <div className="trophy-icon">😢</div>
                <h1>Defeat</h1>
              </>
            )}
          </div>

          <div className="results-players">
            {gameResults.players.map((player, idx) => (
              <div 
                key={idx} 
                className={`result-player ${idx === 0 ? 'winner' : ''} ${player.username === user?.username ? 'you' : ''}`}
              >
                <div className="result-rank">{idx === 0 ? '🥇' : '🥈'}</div>
                <div className="result-info">
                  <span className="result-name">
                    {player.username}
                    {player.username === user?.username && ' (You)'}
                  </span>
                  <span className="result-score">{player.score} points</span>
                  <span className="result-correct">
                    {player.correctAnswers || 0}/{gameResults.totalQuestions} correct
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="results-actions">
            <button className="btn-primary" onClick={resetGame}>
              Play Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Loading/Default
  return (
    <div className="game-screen loading-screen">
      <div className="loader"></div>
      <p>Loading game...</p>
    </div>
  )
}

export default Game
