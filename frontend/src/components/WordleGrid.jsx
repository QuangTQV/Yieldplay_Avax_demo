const CELL_SIZE = 62

const statusColor = {
  correct: '#538d4e',
  present: '#b59f3b',
  absent: '#3a3a3c',
  empty: 'transparent',
  active: 'transparent',
}

const statusBorder = {
  correct: '#538d4e',
  present: '#b59f3b',
  absent: '#3a3a3c',
  empty: '#3a3a3c',
  active: '#999',
}

function Cell({ letter, status }) {
  return (
    <div style={{
      width: CELL_SIZE,
      height: CELL_SIZE,
      border: `2px solid ${statusBorder[status] || statusBorder.empty}`,
      background: statusColor[status] || 'transparent',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 28,
      fontWeight: 800,
      textTransform: 'uppercase',
      color: status && status !== 'empty' && status !== 'active' ? '#fff' : '#fff',
      borderRadius: 4,
      transition: 'background 0.3s, border-color 0.3s',
      userSelect: 'none',
    }}>
      {letter || ''}
    </div>
  )
}

export default function WordleGrid({ submittedGuesses, currentInput, maxAttempts = 6 }) {
  const rows = []

  // Submitted rows
  for (let i = 0; i < submittedGuesses.length; i++) {
    const guess = submittedGuesses[i]
    rows.push(
      <div key={i} style={{ display: 'flex', gap: 6 }}>
        {guess.map((cell, j) => (
          <Cell key={j} letter={cell.letter} status={cell.status} />
        ))}
      </div>
    )
  }

  // Current input row
  if (submittedGuesses.length < maxAttempts) {
    const currentLetters = currentInput.split('')
    rows.push(
      <div key="current" style={{ display: 'flex', gap: 6 }}>
        {Array.from({ length: 5 }).map((_, j) => (
          <Cell key={j} letter={currentLetters[j] || ''} status={currentLetters[j] ? 'active' : 'empty'} />
        ))}
      </div>
    )
  }

  // Empty rows
  const remaining = maxAttempts - submittedGuesses.length - (submittedGuesses.length < maxAttempts ? 1 : 0)
  for (let i = 0; i < remaining; i++) {
    rows.push(
      <div key={`empty-${i}`} style={{ display: 'flex', gap: 6 }}>
        {Array.from({ length: 5 }).map((_, j) => (
          <Cell key={j} letter="" status="empty" />
        ))}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
      {rows}
    </div>
  )
}
