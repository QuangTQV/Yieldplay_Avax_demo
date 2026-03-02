import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useMetaMask } from '../hooks/useMetaMask'

const s = {
  nav: { background: '#1a1a1b', borderBottom: '1px solid #3a3a3c', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', height: 56, position: 'relative' },
  logo: { fontWeight: 800, fontSize: 20, letterSpacing: 2, color: '#fff' },
  logoAccent: { color: '#e84142' },
  links: { display: 'flex', gap: 8, alignItems: 'center' },
  link: (active) => ({ padding: '6px 14px', borderRadius: 8, fontSize: 14, fontWeight: 600, color: active ? '#fff' : '#818384', background: active ? '#6c63ff' : 'transparent' }),
  right: { display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 },
  walletBadge: (correct) => ({
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '5px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600,
    background: correct ? '#1a2a1a' : '#3a1a1a',
    border: `1px solid ${correct ? '#2a7a2a' : '#7a2a2a'}`,
    color: correct ? '#6dff6d' : '#ff6b6b',
    cursor: correct ? 'default' : 'pointer',
    userSelect: 'none',
    transition: 'opacity 0.15s',
  }),
  dot: (correct) => ({ width: 7, height: 7, borderRadius: '50%', background: correct ? '#6dff6d' : '#ff6b6b', flexShrink: 0 }),
  errorToast: {
    position: 'absolute', top: 60, right: 16,
    background: '#3a1a1a', border: '1px solid #7a2a2a',
    color: '#ff6b6b', padding: '8px 14px', borderRadius: 8,
    fontSize: 12, maxWidth: 300, zIndex: 999,
  },
  logoutBtn: { background: '#3a3a3c', color: '#fff', padding: '5px 12px', borderRadius: 6, fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer' },
}

function shortenAddr(addr) {
  if (!addr) return ''
  return addr.slice(0, 6) + '...' + addr.slice(-4)
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const { connected, address, isCorrectChain, error, switchToAvalanche, targetNetwork } = useMetaMask()

  return (
    <nav style={s.nav}>
      <div style={s.logo}>
        Wordle<span style={s.logoAccent}>Play</span>
      </div>

      {user && (
        <div style={s.links}>
          {[
            { to: '/play', label: '🎮 Play' },
            { to: '/leaderboard', label: '🏆 Leaderboard' },
            { to: '/progress', label: '📈 My Progress' },
          ].map(({ to, label }) => (
            <Link key={to} to={to} style={s.link(pathname === to)}>{label}</Link>
          ))}
        </div>
      )}

      <div style={s.right}>
        {connected && address && (
          <div
            style={s.walletBadge(isCorrectChain)}
            title={isCorrectChain ? address : `Click to switch to ${targetNetwork.chainName}`}
            onClick={isCorrectChain ? undefined : switchToAvalanche}
          >
            <div style={s.dot(isCorrectChain)} />
            🦊 {shortenAddr(address)}
            {!isCorrectChain && ' · Switch network →'}
          </div>
        )}

        {user ? (
          <>
            <span style={{ color: '#818384' }}>👤 {user.username}</span>
            <button style={s.logoutBtn} onClick={logout}>Logout</button>
          </>
        ) : (
          <Link to="/login" style={{ ...s.logoutBtn, padding: '5px 12px', textDecoration: 'none', color: '#fff' }}>Login</Link>
        )}
      </div>

      {/* Hiển thị lỗi network switch */}
      {error && (
        <div style={s.errorToast}>⚠ {error}</div>
      )}
    </nav>
  )
}
