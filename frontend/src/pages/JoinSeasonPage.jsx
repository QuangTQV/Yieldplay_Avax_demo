import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useMetaMask } from '../hooks/useMetaMask'
import { getActiveSeason, joinSeason, checkParticipation } from '../api/client'

const s = {
  page: { minHeight: '100vh', background: '#121213', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 },
  card: { background: '#1a1a1b', border: '1px solid #3a3a3c', borderRadius: 16, padding: 40, width: '100%', maxWidth: 480 },
  title: { fontSize: 24, fontWeight: 800, marginBottom: 4 },
  sub: { color: '#818384', fontSize: 14, marginBottom: 28 },
  infoBox: { background: '#121213', border: '1px solid #3a3a3c', borderRadius: 10, padding: 16, marginBottom: 24 },
  row: { display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 14 },
  rowLabel: { color: '#818384' }, rowVal: { fontWeight: 600 },
  stakeInput: { width: '100%', padding: '14px 16px', background: '#121213', border: '1px solid #3a3a3c', borderRadius: 8, color: '#fff', fontSize: 20, fontWeight: 700, outline: 'none', fontFamily: 'inherit', marginBottom: 12, boxSizing: 'border-box' },
  breakdown: { fontSize: 13, color: '#818384', marginBottom: 20, lineHeight: 2 },
  btn: { width: '100%', padding: 14, background: '#538d4e', color: '#fff', borderRadius: 10, fontWeight: 700, fontSize: 16, border: 'none', cursor: 'pointer' },
  skipBtn: { width: '100%', padding: 12, background: 'transparent', color: '#818384', borderRadius: 10, fontWeight: 600, fontSize: 14, border: '1px solid #3a3a3c', cursor: 'pointer', marginTop: 10 },
  error: { background: '#3a1a1a', border: '1px solid #7a2a2a', color: '#ff6b6b', padding: '10px 16px', borderRadius: 8, fontSize: 13, marginBottom: 16 },
  success: { background: '#1a3a1a', border: '1px solid #2a7a2a', color: '#6dff6d', padding: '14px 16px', borderRadius: 8, fontSize: 14, marginBottom: 16 },
  signingCard: { background: '#1a1a2a', border: '1px solid #3a3a6a', borderRadius: 12, padding: 20, marginBottom: 20 },
  signingTitle: { fontWeight: 700, fontSize: 14, marginBottom: 12, color: '#f6851b', display: 'flex', alignItems: 'center', gap: 8 },
  signingRow: { display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '7px 0', borderBottom: '1px solid #2a2a4a' },
  signBtn: { width: '100%', padding: 14, background: '#f6851b', color: '#fff', borderRadius: 10, fontWeight: 800, fontSize: 16, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 },
  txBadge: { background: '#121213', border: '1px solid #3a3a3c', borderRadius: 6, padding: '8px 12px', fontSize: 11, fontFamily: 'monospace', color: '#818384', wordBreak: 'break-all', marginTop: 10 },
  avaxLink: { color: '#e84142', fontSize: 12, textDecoration: 'underline', cursor: 'pointer' },
}

const STEP = { STAKE: 'stake', SIGNING: 'signing', DONE: 'done' }

function MetaMaskIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 318 318" fill="none">
      <path d="M274.1 35.5L174.6 109.4L193 65.8L274.1 35.5Z" fill="#E2761B"/>
      <path d="M44.4 35.5L143.1 110.1L125.6 65.8L44.4 35.5Z" fill="#E4761B"/>
      <path d="M238.3 206.8L211.8 247.4L268.5 263L284.8 207.7L238.3 206.8Z" fill="#E4761B"/>
      <path d="M33.9 207.7L50.1 263L106.8 247.4L80.3 206.8L33.9 207.7Z" fill="#E4761B"/>
    </svg>
  )
}

export default function JoinSeasonPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { connected, address, isCorrectChain, signMessage, switchToAvalanche } = useMetaMask()

  const [season, setSeason] = useState(null)
  const [amount, setAmount] = useState('10')
  const [error, setError] = useState('')
  const [step, setStep] = useState(STEP.STAKE)
  const [joinResult, setJoinResult] = useState(null)
  const [txSig, setTxSig] = useState(null)
  const [signing, setSigning] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const init = async () => {
      try {
        const s = await getActiveSeason()
        setSeason(s)
        // Đã join rồi → vào thẳng game
        if (user?.id) {
          const hasJoined = await checkParticipation(s.id, user.id)
          if (hasJoined) navigate('/play')
        }
      } catch {}
    }
    init()
  }, [user?.id])

  const fee = parseFloat(amount) * 0.02 || 0
  const principal = parseFloat(amount) - fee || 0

  // Step 1: Backend ghi stake, mock gọi YieldPlay /transactions/enter
  const handleJoin = async () => {
    if (!season) return
    setError('')
    if (!connected) { setError('MetaMask chưa kết nối'); return }
    if (!isCorrectChain) { setError('Cần chuyển sang Avalanche Fuji Testnet'); switchToAvalanche(); return }
    const amt = parseFloat(amount)
    if (isNaN(amt) || amt < 1) { setError('Minimum stake is 1 USDC'); return }
    setLoading(true)
    try {
      const result = await joinSeason(user.id, season.id, amt)
      setJoinResult(result)
      setStep(STEP.SIGNING)
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to join season'
      if (msg.includes('Already')) navigate('/play')
      else setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // Step 2: MetaMask ký để xác nhận — demo YieldPlay signing flow
  const handleSign = async () => {
    setSigning(true)
    setError('')
    try {
      /**
       * Production với YieldPlay contract AVAX:
       *   const txHash = await sendTransaction({
       *     to: YIELDPLAY_CONTRACT_ADDRESS,
       *     data: joinResult.encoded_tx_data,   // ABI-encoded calldata
       *     value: ethers.parseUnits(amount, 6).toString(16),
       *   })
       *
       * Demo: dùng personal_sign để MetaMask popup hiện ra thật.
       * User thấy đúng details của giao dịch trước khi ký.
       */
      const message = [
        '=== YieldPlay Season Entry ===',
        '',
        `Network  : Avalanche Fuji Testnet (Chain 43113)`,
        `Season   : ${season.name}`,
        `Amount   : ${joinResult.amount_staked} USDC`,
        `Fee (2%) : ${joinResult.participation_fee} USDC → Reward Pool`,
        `Principal: ${joinResult.principal} USDC → Yield (~4.5% APY)`,
        '',
        `Wallet   : ${address}`,
        `Time     : ${new Date().toISOString()}`,
        '',
        'By signing you confirm this stake on Avalanche.',
      ].join('\n')

      const sig = await signMessage(message)
      setTxSig(sig)
      setStep(STEP.DONE)
    } catch (err) {
      if (err.code === 4001 || err.message?.includes('rejected')) {
        setError('Rejected. Please approve in MetaMask to confirm your stake.')
      } else {
        setError(err.message || 'Signing failed')
      }
    } finally {
      setSigning(false)
    }
  }

  // ── Done ──
  if (step === STEP.DONE) {
    const explorerUrl = `https://testnet.snowtrace.io/address/${address}`
    return (
      <div style={s.page}>
        <div style={s.card}>
          <div style={{ fontSize: 48, textAlign: 'center', marginBottom: 12 }}>🎉</div>
          <h2 style={{ ...s.title, color: '#538d4e', marginBottom: 16, textAlign: 'center' }}>Stake Confirmed!</h2>
          <div style={s.success}>
            <div>Staked: <strong>{joinResult.amount_staked} USDC</strong></div>
            <div>Fee → Reward Pool: <strong>{joinResult.participation_fee} USDC</strong></div>
            <div>Principal earning yield: <strong>{joinResult.principal} USDC</strong></div>
          </div>
          {txSig && (
            <>
              <div style={{ fontSize: 12, color: '#818384', marginBottom: 4 }}>Signature (MetaMask):</div>
              <div style={s.txBadge}>{txSig.slice(0, 66)}...</div>
              <div style={{ marginTop: 8, textAlign: 'right' }}>
                <span style={s.avaxLink} onClick={() => window.open(explorerUrl, '_blank')}>
                  View on Snowtrace ↗
                </span>
              </div>
            </>
          )}
          <p style={{ color: '#818384', fontSize: 13, margin: '20px 0', lineHeight: 1.7 }}>
            Principal đang sinh yield ~4.5% APY trong 30 ngày.
            Yield + fees sẽ phân phối cho top players khi season kết thúc.
          </p>
          <button style={s.btn} onClick={() => navigate('/play')}>Start Playing →</button>
        </div>
      </div>
    )
  }

  // ── Signing step ──
  if (step === STEP.SIGNING) {
    return (
      <div style={s.page}>
        <div style={s.card}>
          <h1 style={s.title}>🦊 Confirm in MetaMask</h1>
          <p style={s.sub}>Review transaction details, then sign in MetaMask</p>
          {error && <div style={s.error}>{error}</div>}
          <div style={s.signingCard}>
            <div style={s.signingTitle}>
              <MetaMaskIcon size={18} /> Transaction Details
            </div>
            {[
              ['Network', 'Avalanche Fuji Testnet'],
              ['Action', 'Stake into Season'],
              ['Season', season?.name],
              ['Amount', `${joinResult?.amount_staked} USDC`],
              ['Fee (2%)', `${joinResult?.participation_fee} USDC → Reward Pool`],
              ['Principal', `${joinResult?.principal} USDC → Yield`],
              ['Wallet', address ? address.slice(0, 20) + '...' : '-'],
            ].map(([k, v]) => (
              <div key={k} style={s.signingRow}>
                <span style={{ color: '#818384' }}>{k}</span>
                <span style={{ fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
          <button style={s.signBtn} onClick={handleSign} disabled={signing || !connected}>
            <MetaMaskIcon size={20} />
            {signing ? 'Waiting for MetaMask...' : 'Sign with MetaMask'}
          </button>
          {!connected && <div style={{ ...s.error, marginTop: 10 }}>MetaMask chưa kết nối</div>}
        </div>
      </div>
    )
  }

  // ── Stake form ──
  return (
    <div style={s.page}>
      <div style={s.card}>
        <h1 style={s.title}>💰 Join Season</h1>
        <p style={s.sub}>Stake USDC to participate and earn yield-backed rewards on Avalanche</p>
        {season && (
          <div style={s.infoBox}>
            {[
              ['Season', season.name],
              ['Duration', `${season.start_date} → ${season.end_date}`],
              ['Reward Pool', `$${season.total_reward_pool.toFixed(2)} USDC`],
              ['Distribution', 'Top 3: 50% / 30% / 20%'],
            ].map(([k, v]) => (
              <div key={k} style={s.row}><span style={s.rowLabel}>{k}</span><span style={s.rowVal}>{v}</span></div>
            ))}
          </div>
        )}
        {error && <div style={s.error}>{error}</div>}
        <label style={{ display: 'block', fontSize: 13, color: '#818384', marginBottom: 8, fontWeight: 600 }}>Stake Amount (USDC)</label>
        <input style={s.stakeInput} type="number" min="1" step="0.5" value={amount} onChange={e => setAmount(e.target.value)} placeholder="10" />
        <div style={s.breakdown}>
          <div>📊 Fee (2%): <strong style={{ color: '#b59f3b' }}>{fee.toFixed(4)} USDC</strong> → Reward Pool</div>
          <div>🔒 Principal: <strong style={{ color: '#538d4e' }}>{principal.toFixed(4)} USDC</strong> → Earning ~4.5% APY</div>
        </div>
        <button style={s.btn} onClick={handleJoin} disabled={loading}>
          {loading ? 'Processing...' : `Stake ${amount} USDC & Join →`}
        </button>
        <button style={s.skipBtn} onClick={() => navigate('/play')}>Skip (view only)</button>
      </div>
    </div>
  )
}
