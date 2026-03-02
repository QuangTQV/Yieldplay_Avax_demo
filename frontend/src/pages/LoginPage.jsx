import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useMetaMask } from '../hooks/useMetaMask'
import { createUser, getUserByWallet, getActiveSeason, checkParticipation } from '../api/client'

const s = {
  page: { minHeight: '100vh', background: '#121213', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 },
  card: { background: '#1a1a1b', border: '1px solid #3a3a3c', borderRadius: 16, padding: 40, width: '100%', maxWidth: 440 },
  title: { fontSize: 28, fontWeight: 800, marginBottom: 8, textAlign: 'center' },
  sub: { color: '#818384', fontSize: 14, textAlign: 'center', marginBottom: 32, lineHeight: 1.7 },
  stepLabel: { fontSize: 11, color: '#818384', fontWeight: 700, letterSpacing: 1.5, marginBottom: 10 },
  mmBtn: (connected) => ({
    width: '100%', padding: '14px 20px',
    background: connected ? '#1a2a1a' : '#f6851b',
    border: `1px solid ${connected ? '#2a7a2a' : 'transparent'}`,
    borderRadius: 12, color: connected ? '#6dff6d' : '#fff',
    fontWeight: 700, fontSize: 15, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    gap: 10, marginBottom: 12, transition: 'all 0.2s',
  }),
  networkBadge: (correct) => ({
    display: 'inline-flex', alignItems: 'center', gap: 6,
    fontSize: 12, padding: '5px 10px',
    background: correct ? '#1a3a1a' : '#3a1a1a',
    border: `1px solid ${correct ? '#2a7a2a' : '#7a2a2a'}`,
    borderRadius: 20, color: correct ? '#6dff6d' : '#ff6b6b',
    marginBottom: 12, cursor: correct ? 'default' : 'pointer',
  }),
  walletBadge: {
    background: '#121213', border: '1px solid #3a3a3c', borderRadius: 8,
    padding: '10px 14px', marginBottom: 16,
    fontSize: 11, color: '#818384', fontFamily: 'monospace',
    display: 'flex', alignItems: 'center', gap: 8, wordBreak: 'break-all',
  },
  divider: { display: 'flex', alignItems: 'center', gap: 12, margin: '4px 0 20px', color: '#3a3a3c', fontSize: 11, fontWeight: 700 },
  dividerLine: { flex: 1, height: 1, background: '#3a3a3c' },
  label: { display: 'block', fontSize: 13, color: '#818384', marginBottom: 6, fontWeight: 600 },
  input: { width: '100%', padding: '12px 16px', background: '#121213', border: '1px solid #3a3a3c', borderRadius: 8, color: '#fff', fontSize: 15, marginBottom: 20, outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' },
  btn: { width: '100%', padding: 14, background: '#6c63ff', color: '#fff', borderRadius: 10, fontWeight: 700, fontSize: 16, border: 'none', cursor: 'pointer' },
  error: { background: '#3a1a1a', border: '1px solid #7a2a2a', color: '#ff6b6b', padding: '10px 16px', borderRadius: 8, fontSize: 13, marginBottom: 16 },
  info: { background: '#1a2a3a', border: '1px solid #2a5a7a', color: '#6db8ff', padding: '10px 16px', borderRadius: 8, fontSize: 13, marginBottom: 16, lineHeight: 1.6 },
  installNote: { textAlign: 'center', fontSize: 12, color: '#818384', marginTop: 12 },
  link: { color: '#f6851b', textDecoration: 'underline', cursor: 'pointer' },
}

function MetaMaskIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 318 318" fill="none">
      <path d="M274.1 35.5L174.6 109.4L193 65.8L274.1 35.5Z" fill="#E2761B" stroke="#E2761B"/>
      <path d="M44.4 35.5L143.1 110.1L125.6 65.8L44.4 35.5Z" fill="#E4761B" stroke="#E4761B"/>
      <path d="M238.3 206.8L211.8 247.4L268.5 263L284.8 207.7L238.3 206.8Z" fill="#E4761B" stroke="#E4761B"/>
      <path d="M33.9 207.7L50.1 263L106.8 247.4L80.3 206.8L33.9 207.7Z" fill="#E4761B" stroke="#E4761B"/>
    </svg>
  )
}

function shortenAddr(addr) {
  if (!addr) return ''
  return addr.slice(0, 6) + '...' + addr.slice(-4)
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const {
    isInstalled, connected, connecting, address,
    isCorrectChain, error: walletError,
    connect, disconnect, switchToAvalanche, targetNetwork,
  } = useMetaMask()

  const [username, setUsername] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('register') // 'register' | 'login'

  const displayError = error || walletError

  const handleConnect = async () => {
    setError('')
    const addr = await connect()
    if (!addr) return

    // Kiểm tra wallet đã đăng ký chưa
    try {
      const existingUser = await getUserByWallet(addr)
      if (existingUser) {
        login(existingUser)
        // Kiểm tra đã join season chưa → redirect đúng chỗ
        try {
          const season = await getActiveSeason()
          const hasJoined = await checkParticipation(season.id, existingUser.id)
          navigate(hasJoined ? '/play' : '/join')
        } catch {
          navigate('/join')
        }
      }
    } catch {
      // 404 = chưa đăng ký → hiện form đăng ký
    }
  }

  const handleSubmit = async () => {
    setError('')
    if (!connected || !address) { setError('Connect MetaMask first'); return }
    if (!isCorrectChain) { setError('Switch to Avalanche Fuji Testnet first'); return }
    if (!username.trim()) { setError('Username is required'); return }
    setLoading(true)
    try {
      const user = await createUser(username.trim(), address)
      login(user)
      navigate('/join')
    } catch (err) {
      const detail = err.response?.data?.detail || 'Registration failed'
      if (detail.includes('Username')) setError('Username taken. Try another.')
      else if (detail.includes('Wallet')) setError('Wallet already registered.')
      else setError(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <h1 style={s.title}>🟩 WordlePlay</h1>
        <p style={s.sub}>
          Compete in a 30-day Wordle season.<br />
          Earn yield-backed rewards on <strong style={{ color: '#e84142' }}>Avalanche</strong>.
        </p>

        {displayError && <div style={s.error}>{displayError}</div>}

        {/* ── Step 1: Connect MetaMask ── */}
        <div style={s.stepLabel}>STEP 1 — CONNECT WALLET</div>

        <button
          style={s.mmBtn(connected)}
          onClick={connected ? disconnect : handleConnect}
          disabled={connecting}
        >
          <MetaMaskIcon />
          {connecting ? 'Connecting...'
            : connected ? `✓ ${shortenAddr(address)}`
            : isInstalled ? 'Connect MetaMask'
            : 'Install MetaMask'}
        </button>

        {/* Network badge */}
        {connected && (
          <div
            style={s.networkBadge(isCorrectChain)}
            onClick={!isCorrectChain ? switchToAvalanche : undefined}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: isCorrectChain ? '#6dff6d' : '#ff6b6b', display: 'inline-block' }} />
            {isCorrectChain
              ? `✓ ${targetNetwork.chainName}`
              : `⚠ Wrong network — click to switch to ${targetNetwork.chainName}`}
          </div>
        )}

        {connected && (
          <div style={s.walletBadge}>
            🦊 <span style={{ color: '#fff' }}>{address}</span>
          </div>
        )}

        {!isInstalled && (
          <div style={s.installNote}>
            MetaMask chưa được cài.{' '}
            <span style={s.link} onClick={() => window.open('https://metamask.io/download/', '_blank')}>
              Tải tại đây
            </span>
            {' '}rồi reload trang.
          </div>
        )}

        {connected && !isCorrectChain && (
          <div style={s.info}>
            Cần chuyển sang <strong>Avalanche Fuji Testnet</strong> để demo.<br />
            Nhấn vào badge đỏ phía trên để tự động thêm network.
          </div>
        )}

        {/* ── Step 2: Username ── */}
        {connected && isCorrectChain && (
          <>
            <div style={s.divider}>
              <div style={s.dividerLine} />
              <span>STEP 2 — CHOOSE USERNAME</span>
              <div style={s.dividerLine} />
            </div>

            <label style={s.label}>Username</label>
            <input
              style={s.input}
              placeholder="wordlemaster"
              value={username}
              onChange={e => setUsername(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !loading && handleSubmit()}
              autoFocus
            />
            <button style={s.btn} onClick={handleSubmit} disabled={loading}>
              {loading ? 'Creating account...' : 'Enter Season →'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
