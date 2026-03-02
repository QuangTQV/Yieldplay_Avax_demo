import { useState, useEffect, useCallback } from 'react'

/**
 * Hook quản lý kết nối Phantom wallet.
 * Dùng window.solana (Phantom inject vào browser) – không cần npm package.
 *
 * Khi tích hợp YieldPlay API thật:
 *   const { publicKey, signAndSendTransaction } = usePhantom()
 *   const txSig = await signAndSendTransaction(serializedTxFromBackend)
 */
export function usePhantom() {
  const [publicKey, setPublicKey] = useState(null)   // string | null
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')

  const phantom = typeof window !== 'undefined' ? window?.solana : null
  const isInstalled = phantom?.isPhantom === true

  // Tự động reconnect nếu đã từng connect trước đó
  useEffect(() => {
    if (!isInstalled) return
    phantom.connect({ onlyIfTrusted: true })
      .then(({ publicKey }) => {
        setPublicKey(publicKey.toString())
        setConnected(true)
      })
      .catch(() => {}) // chưa từng connect → bỏ qua
  }, [isInstalled])

  // Lắng nghe sự kiện từ Phantom
  useEffect(() => {
    if (!phantom) return
    const onConnect = (pk) => { setPublicKey(pk.toString()); setConnected(true) }
    const onDisconnect = () => { setPublicKey(null); setConnected(false) }
    phantom.on('connect', onConnect)
    phantom.on('disconnect', onDisconnect)
    return () => {
      phantom.off('connect', onConnect)
      phantom.off('disconnect', onDisconnect)
    }
  }, [phantom])

  /** Mở popup Phantom để user xác nhận kết nối */
  const connect = useCallback(async () => {
    if (!isInstalled) {
      window.open('https://phantom.app/', '_blank')
      return null
    }
    setConnecting(true)
    setError('')
    try {
      const { publicKey } = await phantom.connect()
      const addr = publicKey.toString()
      setPublicKey(addr)
      setConnected(true)
      return addr
    } catch (err) {
      setError(err.message || 'Connection rejected')
      return null
    } finally {
      setConnecting(false)
    }
  }, [isInstalled, phantom])

  /** Ngắt kết nối */
  const disconnect = useCallback(async () => {
    if (!phantom) return
    await phantom.disconnect()
    setPublicKey(null)
    setConnected(false)
  }, [phantom])

  /**
   * Ký một message (dùng để demo / verify ownership).
   * Mở popup Phantom yêu cầu user ký.
   */
  const signMessage = useCallback(async (message) => {
    if (!phantom || !connected) throw new Error('Wallet not connected')
    const encoded = new TextEncoder().encode(message)
    const { signature } = await phantom.signMessage(encoded, 'utf8')
    // Chuyển Uint8Array → hex string
    return Array.from(signature).map(b => b.toString(16).padStart(2, '0')).join('')
  }, [phantom, connected])

  /**
   * Ký và gửi serialized transaction lên Solana.
   * Dùng khi tích hợp YieldPlay API thật:
   *   const txSig = await signAndSendTransaction(base64SerializedTx)
   *
   * @param {string} base64Tx - serialized transaction từ backend (base64)
   * @returns {string} transaction signature
   */
  const signAndSendTransaction = useCallback(async (base64Tx) => {
    if (!phantom || !connected) throw new Error('Wallet not connected')

    // Decode base64 → Uint8Array
    const txBytes = Uint8Array.from(atob(base64Tx), c => c.charCodeAt(0))

    // Dùng @solana/web3.js Transaction nếu cần deserialize
    // Ở đây dùng sendAndConfirm qua Phantom provider trực tiếp
    const { signature } = await phantom.request({
      method: 'signAndSendTransaction',
      params: { message: base64Tx },
    })
    return signature
  }, [phantom, connected])

  return {
    isInstalled,
    connected,
    connecting,
    publicKey,
    error,
    connect,
    disconnect,
    signMessage,
    signAndSendTransaction,
  }
}
