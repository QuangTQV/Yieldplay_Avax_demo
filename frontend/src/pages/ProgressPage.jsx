import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { getActiveSeason, getSeasonProgress } from '../api/client'

const s = {
  page: { maxWidth: 680, margin: '0 auto', padding: '32px 16px' },
  title: { fontSize: 24, fontWeight: 800, marginBottom: 4 },
  sub: { color: '#818384', fontSize: 14, marginBottom: 28 },
  statsRow: { display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' },
  statCard: {
    flex: 1, minWidth: 120,
    background: '#1a1a1b', border: '1px solid #3a3a3c',
    borderRadius: 12, padding: '16px 20px', textAlign: 'center',
  },
  statVal: { fontSize: 28, fontWeight: 800, color: '#6c63ff' },
  statLabel: { fontSize: 12, color: '#818384', fontWeight: 600, textTransform: 'uppercase', marginTop: 4 },
  calHeader: { fontWeight: 700, fontSize: 16, marginBottom: 12 },
  calendar: { display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6, marginBottom: 28 },
  dayCell: (score, played) => ({
    aspectRatio: '1',
    borderRadius: 6,
    background: !played ? '#1a1a1b' :
      score === 0 ? '#3a1a1a' :
      score < 200 ? '#2a3a1a' :
      score < 400 ? '#1a3a1a' : '#538d4e',
    border: `1px solid ${!played ? '#3a3a3c' : score === 0 ? '#7a2a2a' : '#538d4e'}`,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 10, fontWeight: 700,
    color: !played ? '#3a3a3c' : score === 0 ? '#ff6b6b' : '#fff',
    cursor: 'default',
    title: '',
  }),
  tableHeader: { fontWeight: 700, fontSize: 16, marginBottom: 12 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '10px 12px', textAlign: 'left', color: '#818384', fontSize: 12, fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid #3a3a3c' },
  td: { padding: '12px 12px', fontSize: 14, borderBottom: '1px solid #1f1f20' },
  loading: { color: '#818384', marginTop: 80, textAlign: 'center' },
}

export default function ProgressPage() {
  const { user } = useAuth()
  const [progress, setProgress] = useState(null)
  const [season, setSeason] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const s = await getActiveSeason()
        setSeason(s)
        const p = await getSeasonProgress(s.id, user.id)
        setProgress(p)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div style={s.loading}>Loading your progress...</div>
  if (!progress) return <div style={s.loading}>No progress data found. Play first!</div>

  // Build 30-day calendar
  const startDate = season ? new Date(season.start_date) : new Date()
  const scoreByDate = {}
  progress.daily_scores.forEach(d => {
    scoreByDate[d.play_date] = d
  })

  const calDays = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(startDate)
    d.setDate(d.getDate() + i)
    const key = d.toISOString().slice(0, 10)
    const entry = scoreByDate[key]
    const today = new Date()
    const isFuture = d > today
    return { date: key, day: i + 1, entry, isFuture }
  })

  return (
    <div style={s.page}>
      <h1 style={s.title}>📈 My Season Progress</h1>
      <p style={s.sub}>{season?.name} · Rank #{progress.current_rank} of {progress.total_players}</p>

      <div style={s.statsRow}>
        {[
          { val: progress.total_score.toLocaleString(), label: 'Total Score' },
          { val: `#${progress.current_rank}`, label: 'Current Rank' },
          { val: progress.days_won, label: 'Days Won' },
          { val: progress.days_played, label: 'Days Played' },
        ].map(({ val, label }) => (
          <div key={label} style={s.statCard}>
            <div style={s.statVal}>{val}</div>
            <div style={s.statLabel}>{label}</div>
          </div>
        ))}
      </div>

      <div style={s.calHeader}>30-Day Calendar</div>
      <div style={s.calendar}>
        {calDays.map(({ date, day, entry, isFuture }) => {
          const played = !!entry
          const score = entry?.score ?? 0
          return (
            <div
              key={date}
              style={{
                ...s.dayCell(score, played),
                opacity: isFuture ? 0.3 : 1,
              }}
              title={`${date}: ${played ? `${score} pts` : 'not played'}`}
            >
              {day}
            </div>
          )
        })}
      </div>

      <div style={s.tableHeader}>Daily Results</div>
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>Date</th>
            <th style={s.th}>Result</th>
            <th style={s.th}>Score</th>
            <th style={s.th}>Attempts</th>
          </tr>
        </thead>
        <tbody>
          {progress.daily_scores
            .slice()
            .sort((a, b) => b.play_date.localeCompare(a.play_date))
            .map((day) => (
              <tr key={day.play_date}>
                <td style={s.td}>{day.play_date}</td>
                <td style={s.td}>
                  {day.won
                    ? <span style={{ color: '#538d4e', fontWeight: 700 }}>✅ Won</span>
                    : <span style={{ color: '#ff6b6b', fontWeight: 700 }}>❌ Lost</span>
                  }
                </td>
                <td style={s.td}><strong style={{ color: '#6c63ff' }}>{day.score}</strong></td>
                <td style={s.td}>{day.attempts_count}/6</td>
              </tr>
            ))
          }
          {progress.daily_scores.length === 0 && (
            <tr>
              <td colSpan={4} style={{ ...s.td, color: '#818384', textAlign: 'center', padding: 32 }}>
                No games played yet. Start playing!
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
