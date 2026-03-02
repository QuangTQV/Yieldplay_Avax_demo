import { useState, useEffect } from 'react'
import { getActiveSeason, getLeaderboard } from '../api/client'
import { useAuth } from '../hooks/useAuth'

const rankColor = { 1: '#f5c518', 2: '#c0c0c0', 3: '#cd7f32' }
const rankIcon = { 1: '🥇', 2: '🥈', 3: '🥉' }

const s = {
  page: { maxWidth: 700, margin: '0 auto', padding: '32px 16px' },
  header: { marginBottom: 28 },
  title: { fontSize: 24, fontWeight: 800, marginBottom: 4 },
  sub: { color: '#818384', fontSize: 14 },
  poolCard: {
    background: '#1a1a1b', border: '1px solid #3a3a3c',
    borderRadius: 12, padding: 20, marginBottom: 24,
    display: 'flex', gap: 32, flexWrap: 'wrap',
  },
  poolStat: { flex: 1 },
  poolLabel: { color: '#818384', fontSize: 12, fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 },
  poolValue: { fontSize: 22, fontWeight: 800, color: '#6c63ff' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    padding: '12px 16px', textAlign: 'left',
    color: '#818384', fontSize: 12, fontWeight: 600,
    textTransform: 'uppercase', borderBottom: '1px solid #3a3a3c',
  },
  tr: (isMe, rank) => ({
    borderBottom: '1px solid #1f1f20',
    background: isMe ? '#1a1a2f' : 'transparent',
    transition: 'background 0.15s',
  }),
  td: { padding: '14px 16px', fontSize: 15 },
  rank: (rank) => ({
    fontWeight: 800, fontSize: 16,
    color: rankColor[rank] || '#818384',
  }),
  username: (isMe) => ({
    fontWeight: isMe ? 700 : 400,
    color: isMe ? '#6c63ff' : '#fff',
  }),
  score: { fontWeight: 700, color: '#fff' },
  loading: { color: '#818384', marginTop: 60, textAlign: 'center' },
}

export default function LeaderboardPage() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const season = await getActiveSeason()
        const lb = await getLeaderboard(season.id)
        setData(lb)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div style={s.loading}>Loading leaderboard...</div>
  if (!data) return <div style={s.loading}>No season data found</div>

  return (
    <div style={s.page}>
      <div style={s.header}>
        <h1 style={s.title}>🏆 Season Leaderboard</h1>
        <p style={s.sub}>{data.season.name} · {data.season.start_date} → {data.season.end_date}</p>
      </div>

      <div style={s.poolCard}>
        <div style={s.poolStat}>
          <div style={s.poolLabel}>Reward Pool</div>
          <div style={s.poolValue}>${data.reward_pool.toFixed(2)} USDC</div>
        </div>
        <div style={s.poolStat}>
          <div style={s.poolLabel}>Players</div>
          <div style={s.poolValue}>{data.total_players}</div>
        </div>
        <div style={s.poolStat}>
          <div style={s.poolLabel}>Distribution</div>
          <div style={{ fontSize: 13, color: '#818384', marginTop: 4 }}>
            🥇 50% · 🥈 30% · 🥉 20%
          </div>
        </div>
      </div>

      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>#</th>
            <th style={s.th}>Player</th>
            <th style={s.th}>Season Score</th>
            <th style={s.th}>Days Won</th>
            <th style={s.th}>Days Played</th>
          </tr>
        </thead>
        <tbody>
          {data.leaderboard.map((entry) => {
            const isMe = String(entry.user_id) === String(user?.id)
            return (
              <tr key={entry.user_id} style={s.tr(isMe, entry.rank)}>
                <td style={s.td}>
                  <span style={s.rank(entry.rank)}>
                    {rankIcon[entry.rank] || `#${entry.rank}`}
                  </span>
                </td>
                <td style={s.td}>
                  <span style={s.username(isMe)}>
                    {entry.username} {isMe && '(you)'}
                  </span>
                </td>
                <td style={s.td}><span style={s.score}>{entry.season_score.toLocaleString()}</span></td>
                <td style={s.td}><span style={{ color: '#538d4e', fontWeight: 600 }}>{entry.days_won}</span></td>
                <td style={s.td}><span style={{ color: '#818384' }}>{entry.days_played}</span></td>
              </tr>
            )
          })}
          {data.leaderboard.length === 0 && (
            <tr>
              <td colSpan={5} style={{ ...s.td, color: '#818384', textAlign: 'center', padding: 40 }}>
                No players yet. Be the first!
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
