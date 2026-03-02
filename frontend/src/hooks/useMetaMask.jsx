import { useState, useEffect, useCallback, useContext, createContext } from 'react'

export const AVAX_FUJI = {
  chainId: '0xa869',   // 43113 — lowercase hex, MetaMask yêu cầu format này
  chainName: 'Avalanche Fuji Testnet',
  nativeCurrency: { name: 'AVAX', symbol: 'AVAX', decimals: 18 },
  rpcUrls: ['https://api.avax-test.network/ext/bc/C/rpc'],
  blockExplorerUrls: ['https://testnet.snowtrace.io'],
}

const TARGET_CHAIN_ID = AVAX_FUJI.chainId  // '0xa869'

// ── Context để share state giữa tất cả components ─────────────────────────────
const MetaMaskContext = createContext(null)

export function MetaMaskProvider({ children }) {
  const [address, setAddress]           = useState(null)
  const [connected, setConnected]       = useState(false)
  const [connecting, setConnecting]     = useState(false)
  const [chainId, setChainId]           = useState(null)
  const [error, setError]               = useState('')

  const ethereum = typeof window !== 'undefined' ? window?.ethereum : null
  const isInstalled = !!ethereum?.isMetaMask

  // Normalize chainId về lowercase hex để so sánh nhất quán
  const normalizeChain = (id) => id ? id.toLowerCase() : null
  const isCorrectChain = normalizeChain(chainId) === TARGET_CHAIN_ID

  // Đọc trạng thái ban đầu khi mount
  useEffect(() => {
    if (!ethereum) return
    ethereum.request({ method: 'eth_chainId' })
      .then(id => setChainId(normalizeChain(id)))
      .catch(() => {})
    ethereum.request({ method: 'eth_accounts' })
      .then(accounts => {
        if (accounts.length > 0) { setAddress(accounts[0]); setConnected(true) }
      })
      .catch(() => {})
  }, [ethereum])

  // Lắng nghe sự kiện MetaMask
  useEffect(() => {
    if (!ethereum) return
    const onAccountsChanged = (accounts) => {
      if (accounts.length > 0) { setAddress(accounts[0]); setConnected(true) }
      else { setAddress(null); setConnected(false) }
    }
    const onChainChanged = (id) => {
      setChainId(normalizeChain(id))
      // KHÔNG reload page — tự update state
    }
    ethereum.on('accountsChanged', onAccountsChanged)
    ethereum.on('chainChanged', onChainChanged)
    return () => {
      ethereum.removeListener('accountsChanged', onAccountsChanged)
      ethereum.removeListener('chainChanged', onChainChanged)
    }
  }, [ethereum])

  // ── Switch / Add Avalanche Fuji ─────────────────────────────────────────────
  const switchToAvalanche = useCallback(async () => {
    if (!ethereum) { setError('MetaMask không tìm thấy'); return false }
    setError('')
    try {
      // Thử switch trước
      await ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: AVAX_FUJI.chainId }],
      })
      return true
    } catch (err) {
      // 4902 hoặc -32603 = chain chưa có trong MetaMask → thêm mới
      if (err.code === 4902 || err.code === -32603) {
        try {
          await ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [AVAX_FUJI],
          })
          return true
        } catch (addErr) {
          setError(addErr.code === 4001
            ? 'Bạn đã từ chối thêm Avalanche network.'
            : `Không thể thêm network: ${addErr.message}`)
          return false
        }
      }
      setError(err.code === 4001
        ? 'Bạn đã từ chối chuyển network.'
        : `Lỗi: ${err.message}`)
      return false
    }
  }, [ethereum])

  // ── Connect ─────────────────────────────────────────────────────────────────
  const connect = useCallback(async () => {
    if (!isInstalled) { window.open('https://metamask.io/download/', '_blank'); return null }
    setConnecting(true)
    setError('')
    try {
      const accounts = await ethereum.request({ method: 'eth_requestAccounts' })
      const addr = accounts[0]
      setAddress(addr)
      setConnected(true)

      const currentChain = await ethereum.request({ method: 'eth_chainId' })
      setChainId(normalizeChain(currentChain))

      if (normalizeChain(currentChain) !== TARGET_CHAIN_ID) {
        await switchToAvalanche()
      }
      return addr
    } catch (err) {
      setError(err.code === 4001 ? 'Kết nối bị từ chối.' : err.message || 'Lỗi kết nối')
      return null
    } finally {
      setConnecting(false)
    }
  }, [isInstalled, ethereum, switchToAvalanche])

  const disconnect = useCallback(() => {
    setAddress(null); setConnected(false)
  }, [])

  const signMessage = useCallback(async (message) => {
    if (!ethereum || !connected) throw new Error('Wallet chưa kết nối')
    return ethereum.request({ method: 'personal_sign', params: [message, address] })
  }, [ethereum, connected, address])

  const sendTransaction = useCallback(async (tx) => {
    if (!ethereum || !connected) throw new Error('Wallet chưa kết nối')
    if (!isCorrectChain) { await switchToAvalanche() }
    return ethereum.request({
      method: 'eth_sendTransaction',
      params: [{ from: address, ...tx }],
    })
  }, [ethereum, connected, address, isCorrectChain, switchToAvalanche])

  const value = {
    isInstalled, connected, connecting,
    address, chainId, isCorrectChain, error,
    connect, disconnect, signMessage, sendTransaction, switchToAvalanche,
    targetNetwork: AVAX_FUJI,
  }

  return (
    <MetaMaskContext.Provider value={value}>
      {children}
    </MetaMaskContext.Provider>
  )
}

// ── Hook dùng trong components ─────────────────────────────────────────────────
export function useMetaMask() {
  const ctx = useContext(MetaMaskContext)
  if (!ctx) throw new Error('useMetaMask phải được dùng bên trong MetaMaskProvider')
  return ctx
}
