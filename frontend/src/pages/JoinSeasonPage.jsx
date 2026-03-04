import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  checkParticipation,
  getActiveSeason,
  joinSeasonConfirm,
  joinSeasonPrepare,
} from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { useMetaMask } from '../hooks/useMetaMask'

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
  btnDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  skipBtn: { width: '100%', padding: 12, background: 'transparent', color: '#818384', borderRadius: 10, fontWeight: 600, fontSize: 14, border: '1px solid #3a3a3c', cursor: 'pointer', marginTop: 10 },
  error: { background: '#3a1a1a', border: '1px solid #7a2a2a', color: '#ff6b6b', padding: '10px 16px', borderRadius: 8, fontSize: 13, marginBottom: 16 },
  success: { background: '#1a3a1a', border: '1px solid #2a7a2a', color: '#6dff6d', padding: '14px 16px', borderRadius: 8, fontSize: 14, marginBottom: 16 },
  signingCard: { background: '#1a1a2a', border: '1px solid #3a3a6a', borderRadius: 12, padding: 20, marginBottom: 20 },
  signingTitle: { fontWeight: 700, fontSize: 14, marginBottom: 12, color: '#f6851b', display: 'flex', alignItems: 'center', gap: 8 },
  signingRow: { display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '7px 0', borderBottom: '1px solid #2a2a4a' },
  signBtn: { width: '100%', padding: 14, background: '#f6851b', color: '#fff', borderRadius: 10, fontWeight: 800, fontSize: 16, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 },
  txBadge: { background: '#121213', border: '1px solid #3a3a3c', borderRadius: 6, padding: '8px 12px', fontSize: 11, fontFamily: 'monospace', color: '#818384', wordBreak: 'break-all', marginTop: 10 },
  confirmingBox: { background: '#1a1a2a', border: '1px solid #3a3a6a', borderRadius: 10, padding: 20, marginBottom: 20, textAlign: 'center' },
  spinner: { display: 'inline-block', width: 24, height: 24, border: '3px solid #3a3a6a', borderTop: '3px solid #f6851b', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: 12 },
}

const STEP = {
  STAKE:       'stake',       // nhập amount
  SIGNING:     'signing',     // hiển thị tx details, chờ MetaMask
  CONFIRMING:  'confirming',  // tx đã gửi, chờ on-chain confirmation
  DONE:        'done',        // confirmed + DB ghi xong
}

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
  const navigate  = useNavigate()
  const { connected, address, isCorrectChain, switchToAvalanche } = useMetaMask()

  const [season,      setSeason]      = useState(null)
  const [amount,      setAmount]      = useState('10')
  const [error,       setError]       = useState('')
  const [step,        setStep]        = useState(STEP.STAKE)
  const [prepareData, setPrepareData] = useState(null)  // response từ /join/prepare
  const [txHash,      setTxHash]      = useState('')
  const [confirmData, setConfirmData] = useState(null)  // response từ /join/confirm
  const [loading,     setLoading]     = useState(false)

  // ── Init ─────────────────────────────────────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      try {
        const activeSeason = await getActiveSeason()
        setSeason(activeSeason)
        if (user?.id) {
          const hasJoined = await checkParticipation(activeSeason.id, user.id)
          if (hasJoined) navigate('/play')
        }
      } catch {}
    }
    init()
  }, [user?.id])

  const amountFloat = parseFloat(amount) || 0

  // ── Step 1: Validate + build unsigned tx từ server ───────────────────────────
  const handlePrepare = async () => {
    setError('')
    if (!connected)       { setError('MetaMask chưa kết nối'); return }
    if (!isCorrectChain)  { setError('Cần chuyển sang đúng network'); switchToAvalanche(); return }
    if (amountFloat < 1)  { setError('Minimum stake is 1 USDC'); return }
    if (!season)          return

    setLoading(true)
    try {
      // Gọi /seasons/join/prepare → server validate + build unsigned tx
      // Nếu allowance thấp, server trả 400 "Call /tx/build/approve first"
      const data = await joinSeasonPrepare(user.id, season.id, amountFloat)
      setPrepareData(data)
      setStep(STEP.SIGNING)
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Failed to prepare transaction'
      if (detail.includes('Already joined')) navigate('/play')
      // Nếu cần approve trước → hướng dẫn user
      else if (detail.includes('approve')) setError(`Token chưa được approve. ${detail}`)
      else setError(detail)
    } finally {
      setLoading(false)
    }
  }

  // ── Step 2: Gửi tx thật qua MetaMask (sendTransaction) ───────────────────────
  const handleSendTransaction = async () => {
    setError('')
    setLoading(true)
    try {
      const unsignedTx = prepareData.unsigned_tx

      /**
       * Gửi tx thật qua MetaMask eth_sendTransaction.
       * MetaMask sẽ popup yêu cầu user confirm gas + sign.
       *
       * unsignedTx shape (từ /tx/build/deposit):
       *   { to, data, gas, nonce, chainId, value, gasPrice? }
       *
       * Dùng window.ethereum trực tiếp để pass đúng hex format.
       */
      const txParams = {
        from:  address,
        to:    unsignedTx.to,
        data:  unsignedTx.data,
        gas:   '0x' + unsignedTx.gas.toString(16),
        value: '0x' + (unsignedTx.value || 0).toString(16),
        // gasPrice hoặc EIP-1559 fields
        ...(unsignedTx.maxFeePerGas
          ? {
              maxFeePerGas:         '0x' + unsignedTx.maxFeePerGas.toString(16),
              maxPriorityFeePerGas: '0x' + unsignedTx.maxPriorityFeePerGas.toString(16),
            }
          : {
              gasPrice: '0x' + unsignedTx.gasPrice.toString(16),
            }),
      }

      // eth_sendTransaction → MetaMask popup → user confirm → trả tx hash
      const hash = await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [txParams],
      })

      setTxHash(hash)
      setStep(STEP.CONFIRMING)

      // Sau khi có hash → gọi confirm để server verify on-chain + ghi DB
      await handleConfirm(hash)
    } catch (err) {
      if (err.code === 4001 || err.message?.includes('rejected')) {
        setError('Transaction rejected. Please approve in MetaMask.')
      } else {
        setError(err.message || 'Transaction failed')
      }
    } finally {
      setLoading(false)
    }
  }

  // ── Step 3: Confirm với server sau khi broadcast ─────────────────────────────
  const handleConfirm = async (hash) => {
    try {
      // Server verify tx status on-chain → ghi SeasonParticipant vào DB
      const data = await joinSeasonConfirm(user.id, season.id, amountFloat, hash)
      setConfirmData(data)
      setStep(STEP.DONE)
    } catch (err) {
      // Tx đã broadcast nhưng confirm thất bại (chưa mined, node chậm...)
      // Không báo lỗi ngay — giữ ở CONFIRMING, user có thể retry
      const detail = err.response?.data?.detail || err.message || ''
      if (detail.includes('not yet confirmed')) {
        setError('Transaction chưa được confirm. Vui lòng đợi thêm và thử lại.')
      } else {
        setError(`Confirm failed: ${detail}`)
        // Vẫn ở CONFIRMING để user có thể retry confirm thủ công
      }
    }
  }

  // ── DONE ─────────────────────────────────────────────────────────────────────
  if (step === STEP.DONE) {
    return (
      <div style={s.page}>
        <div style={s.card}>
          <div style={{ fontSize: 48, textAlign: 'center', marginBottom: 12 }}>🎉</div>
          <h2 style={{ ...s.title, color: '#538d4e', marginBottom: 16, textAlign: 'center' }}>
            Stake Confirmed!
          </h2>
          <div style={s.success}>
            <div>Staked: <strong>{confirmData?.amount_deposited ?? amountFloat} USDC</strong></div>
            <div>Transaction confirmed on-chain ✓</div>
          </div>
          {txHash && (
            <>
              <div style={{ fontSize: 12, color: '#818384', marginBottom: 4 }}>Transaction Hash:</div>
              <div style={s.txBadge}>{txHash}</div>
              <div style={{ marginTop: 8, textAlign: 'right' }}>
                <span
                  style={{ color: '#e84142', fontSize: 12, textDecoration: 'underline', cursor: 'pointer' }}
                  onClick={() => window.open(`https://sepolia.etherscan.io/tx/${txHash}`, '_blank')}
                >
                  View on Etherscan ↗
                </span>
              </div>
            </>
          )}
          <p style={{ color: '#818384', fontSize: 13, margin: '20px 0', lineHeight: 1.7 }}>
            Principal đang sinh yield trong vault.
            Yield + fees sẽ phân phối cho top players khi season kết thúc.
          </p>
          <button style={s.btn} onClick={() => navigate('/play')}>
            Start Playing →
          </button>
        </div>
      </div>
    )
  }

  // ── CONFIRMING (tx đã broadcast, chờ on-chain) ────────────────────────────────
  if (step === STEP.CONFIRMING) {
    return (
      <div style={s.page}>
        <div style={s.card}>
          <h1 style={s.title}>⏳ Confirming...</h1>
          <p style={s.sub}>Transaction đã được gửi, đang chờ on-chain confirmation</p>
          {error && (
            <>
              <div style={s.error}>{error}</div>
              <button style={s.btn} onClick={() => handleConfirm(txHash)} disabled={loading}>
                {loading ? 'Retrying...' : 'Retry Confirm'}
              </button>
            </>
          )}
          {!error && (
            <div style={s.confirmingBox}>
              <div style={s.spinner} />
              <div style={{ color: '#818384', fontSize: 13 }}>Waiting for block confirmation...</div>
              {txHash && <div style={s.txBadge}>{txHash}</div>}
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── SIGNING (hiển thị tx details, chờ MetaMask) ───────────────────────────────
  if (step === STEP.SIGNING) {
    const tx = prepareData?.unsigned_tx
    return (
      <div style={s.page}>
        <div style={s.card}>
          <h1 style={s.title}>🦊 Confirm in MetaMask</h1>
          <p style={s.sub}>Review transaction details, then confirm in MetaMask</p>
          {error && <div style={s.error}>{error}</div>}

          <div style={s.signingCard}>
            <div style={s.signingTitle}>
              <MetaMaskIcon size={18} /> Transaction Details
            </div>
            {[
              ['Action',    'Deposit into YieldPlay round'],
              ['Season',    season?.name],
              ['Amount',    `${amountFloat} USDC`],
              ['Contract',  tx?.to ? tx.to.slice(0, 20) + '...' : '-'],
              ['Gas Limit', tx?.gas?.toLocaleString() ?? '-'],
              ['Wallet',    address ? address.slice(0, 20) + '...' : '-'],
            ].map(([k, v]) => (
              <div key={k} style={s.signingRow}>
                <span style={{ color: '#818384' }}>{k}</span>
                <span style={{ fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>

          <button
            style={{ ...s.signBtn, ...(loading ? s.btnDisabled : {}) }}
            onClick={handleSendTransaction}
            disabled={loading || !connected}
          >
            <MetaMaskIcon size={20} />
            {loading ? 'Waiting for MetaMask...' : 'Send Transaction'}
          </button>

          {!connected && (
            <div style={{ ...s.error, marginTop: 10 }}>MetaMask chưa kết nối</div>
          )}

          <button
            style={{ ...s.skipBtn }}
            onClick={() => { setStep(STEP.STAKE); setPrepareData(null); setError('') }}
          >
            ← Back
          </button>
        </div>
      </div>
    )
  }

  // ── STAKE form ────────────────────────────────────────────────────────────────
  return (
    <div style={s.page}>
      <div style={s.card}>
        <h1 style={s.title}>💰 Join Season</h1>
        <p style={s.sub}>Stake USDC to participate and earn yield-backed rewards</p>

        {season && (
          <div style={s.infoBox}>
            {[
              ['Season',       season.name],
              ['Duration',     `${season.start_date} → ${season.end_date}`],
              ['Reward Pool',  `$${(season.total_reward_pool || 0).toFixed(2)} USDC`],
              ['Distribution', 'Top 3: 50% / 30% / 20%'],
            ].map(([k, v]) => (
              <div key={k} style={s.row}>
                <span style={s.rowLabel}>{k}</span>
                <span style={s.rowVal}>{v}</span>
              </div>
            ))}
          </div>
        )}

        {error && <div style={s.error}>{error}</div>}

        <label style={{ display: 'block', fontSize: 13, color: '#818384', marginBottom: 8, fontWeight: 600 }}>
          Stake Amount (USDC)
        </label>
        <input
          style={s.stakeInput}
          type="number" min="1" step="0.5"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          placeholder="10"
        />
        <div style={s.breakdown}>
          <div>🔒 Principal: <strong style={{ color: '#538d4e' }}>{amountFloat.toFixed(4)} USDC</strong> → Earning yield in vault</div>
        </div>

        <button
          style={{ ...s.btn, ...(loading ? s.btnDisabled : {}) }}
          onClick={handlePrepare}
          disabled={loading}
        >
          {loading ? 'Preparing...' : `Stake ${amount} USDC & Join →`}
        </button>
        <button style={s.skipBtn} onClick={() => navigate('/play')}>
          Skip (view only)
        </button>
      </div>
    </div>
  )
}