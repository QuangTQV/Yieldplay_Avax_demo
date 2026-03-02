import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../hooks/useAuth'
import { startGame, submitGuess } from '../api/client'
import WordleGrid from '../components/WordleGrid'
import Keyboard from '../components/Keyboard'

const s = {
  page: { minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 16px' },
  header: { textAlign: 'center', marginBottom: 20 },
  title: { fontSize: 22, fontWeight: 800, letterSpacing: 2, textTransform: 'uppercase' },
  date: { color: '#818384', fontSize: 13, marginTop: 4 },
  toast: (type) => ({
    position: 'fixed', top: 72, left: '50%', transform: 'translateX(-50%)',
    background: type === 'error' ? '#3a1a1a' : type === 'win' ? '#1a3a1a' : '#1a1a2a',
    border: `1px solid ${type === 'error' ? '#7a2a2a' : type === 'win' ? '#2a7a2a' : '#3a3a7a'}`,
    color: type === 'error' ? '#ff6b6b' : type === 'win' ? '#6dff6d' : '#fff',
    padding: '12px 24px', borderRadius: 10, fontWeight: 700, fontSize: 15,
    zIndex: 999, whiteSpace: 'nowrap',
  }),
  resultCard: {
    background: '#1a1a1b', border: '1px solid #3a3a3c',
    borderRadius: 16, padding: 24, marginTop: 24,
    textAlign: 'center', maxWidth: 340, width: '100%',
  },
  scoreNum: { fontSize: 48, fontWeight: 800, color: '#6c63ff' },
  grid: { margin: '16px 0 20px' },
  kbd: { margin: '8px 0 0' },
  loading: { color: '#818384', marginTop: 80, fontSize: 16 },
}

export default function GamePage() {
  const { user } = useAuth()
  const [gameState, setGameState] = useState(null)
  const [currentInput, setCurrentInput] = useState('')
  const [toast, setToast] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const showToast = (msg, type = 'info', duration = 2500) => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), duration)
  }

  useEffect(() => {
    loadGame()
  }, [])

  const loadGame = async () => {
    try {
      const state = await startGame(user.id)
      setGameState(state)
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to load game'
      showToast(msg, 'error', 5000)
    } finally {
      setLoading(false)
    }
  }

  // Build letter status map from all submitted guesses
  const letterStatuses = {}
  if (gameState?.guesses) {
    for (const row of gameState.guesses) {
      for (const cell of row) {
        const existing = letterStatuses[cell.letter]
        const priority = { correct: 3, present: 2, absent: 1 }
        if (!existing || priority[cell.status] > priority[existing]) {
          letterStatuses[cell.letter] = cell.status
        }
      }
    }
  }

  const handleKey = useCallback(async (key) => {
    if (!gameState || gameState.completed || submitting) return

    if (key === '⌫' || key === 'Backspace') {
      setCurrentInput(prev => prev.slice(0, -1))
      return
    }
    if (key === 'Enter') {
      if (currentInput.length !== 5) {
        showToast('Word must be 5 letters', 'error', 1500)
        return
      }
      setSubmitting(true)
      try {
        const result = await submitGuess(user.id, currentInput)
        setCurrentInput('')
        setGameState(prev => ({
          ...prev,
          guesses: [...prev.guesses, result.result],
          attempts_used: result.attempts_used,
          completed: result.completed,
          won: result.won,
          score: result.score,
          answer: result.answer,
        }))
        if (result.won) {
          showToast(`🎉 Genius! Score: ${result.score}`, 'win', 4000)
        } else if (result.completed) {
          showToast(`Game over! Answer: ${result.answer?.toUpperCase()}`, 'error', 5000)
        }
      } catch (err) {
        const msg = err.response?.data?.detail || 'Something went wrong'
        showToast(msg, 'error', 2000)
        // Không clear input để user thấy từ nào bị lỗi
      } finally {
        setSubmitting(false)
      }
      return
    }

    if (/^[a-zA-Z]$/.test(key) && currentInput.length < 5) {
      setCurrentInput(prev => prev + key.toLowerCase())
    }
  }, [gameState, currentInput, submitting, user.id])

  // Physical keyboard
  useEffect(() => {
    const handler = (e) => handleKey(e.key)
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleKey])

  if (loading) return <div style={s.loading}>Loading today's puzzle...</div>

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })

  return (
    <div style={s.page}>
      {toast && <div style={s.toast(toast.type)}>{toast.msg}</div>}

      <div style={s.header}>
        <div style={s.title}>Today's Wordle</div>
        <div style={s.date}>{today}</div>
      </div>

      <div style={s.grid}>
        <WordleGrid
          submittedGuesses={gameState?.guesses || []}
          currentInput={gameState?.completed ? '' : currentInput}
        />
      </div>

      {gameState?.completed ? (
        <div style={s.resultCard}>
          {gameState.won ? (
            <>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎉</div>
              <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Solved!</div>
              <div style={s.scoreNum}>{gameState.score}</div>
              <div style={{ color: '#818384', fontSize: 13, marginTop: 4 }}>points earned today</div>
              <div style={{ color: '#818384', fontSize: 13, marginTop: 12 }}>
                {gameState.attempts_used} attempts · Check leaderboard for your rank
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: 32, marginBottom: 8 }}>😞</div>
              <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Better luck tomorrow</div>
              <div style={{ color: '#818384', fontSize: 14 }}>
                Answer: <strong style={{ color: '#fff', textTransform: 'uppercase' }}>{gameState.answer}</strong>
              </div>
              <div style={{ color: '#818384', fontSize: 13, marginTop: 12 }}>0 points • Come back tomorrow!</div>
            </>
          )}
        </div>
      ) : (
        <div style={s.kbd}>
          <Keyboard
            onKey={handleKey}
            letterStatuses={letterStatuses}
            disabled={submitting}
          />
        </div>
      )}
    </div>
  )
}
