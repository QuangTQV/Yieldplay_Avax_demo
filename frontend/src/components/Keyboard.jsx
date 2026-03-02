const ROWS = [
  ['q','w','e','r','t','y','u','i','o','p'],
  ['a','s','d','f','g','h','j','k','l'],
  ['Enter','z','x','c','v','b','n','m','⌫'],
]

function getKeyColor(key, letterStatuses) {
  const status = letterStatuses[key]
  if (status === 'correct') return { bg: '#538d4e', color: '#fff' }
  if (status === 'present') return { bg: '#b59f3b', color: '#fff' }
  if (status === 'absent') return { bg: '#3a3a3c', color: '#818384' }
  return { bg: '#818384', color: '#fff' }
}

export default function Keyboard({ onKey, letterStatuses = {}, disabled }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'center' }}>
      {ROWS.map((row, ri) => (
        <div key={ri} style={{ display: 'flex', gap: 6 }}>
          {row.map((key) => {
            const { bg, color } = getKeyColor(key.toLowerCase(), letterStatuses)
            const isWide = key === 'Enter' || key === '⌫'
            return (
              <button
                key={key}
                disabled={disabled}
                onClick={() => onKey(key)}
                style={{
                  width: isWide ? 66 : 44,
                  height: 58,
                  background: bg,
                  color,
                  fontWeight: 700,
                  fontSize: isWide ? 12 : 16,
                  borderRadius: 6,
                  textTransform: 'uppercase',
                  transition: 'background 0.2s',
                  border: 'none',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  opacity: disabled ? 0.5 : 1,
                }}
              >
                {key}
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}
