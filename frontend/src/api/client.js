import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Users ──────────────────────────────────────────────────────────────────────
export const createUser = (username, walletAddress) =>
  api.post('/users', { username, wallet_address: walletAddress }).then(r => r.data)

export const getUser = (userId) =>
  api.get(`/users/${userId}`).then(r => r.data)

export const getUserByWallet = (walletAddress) =>
  api.get('/users', { params: { wallet_address: walletAddress } }).then(r => r.data)

// ── Seasons ────────────────────────────────────────────────────────────────────
export const getActiveSeason = () =>
  api.get('/seasons/active').then(r => r.data)

export const getSeason = (seasonId) =>
  api.get(`/seasons/${seasonId}`).then(r => r.data)

export const checkParticipation = (seasonId, userId) =>
  api.get(`/seasons/check/${seasonId}/${userId}`).then(r => r.data)

/**
 * Non-custodial join flow — 2 bước:
 *
 * Step 1: joinSeasonPrepare()
 *   → Server validate + build unsigned tx
 *   → Trả { unsigned_tx, amount_wei, token_address, ... }
 *   → Frontend ký bằng MetaMask (sendTransaction)
 *
 * Step 2: joinSeasonConfirm()
 *   → Frontend gửi tx_hash sau khi broadcast
 *   → Server verify on-chain → ghi DB
 *   → Trả { participant_id, amount_deposited, tx_hash }
 */
export const joinSeasonPrepare = (userId, seasonId, amountStaked) =>
  api.post('/seasons/join/prepare', {
    user_id:       userId,
    season_id:     seasonId,
    amount_staked: amountStaked,
  }).then(r => r.data)

export const joinSeasonConfirm = (userId, seasonId, amountStaked, txHash) =>
  api.post('/seasons/join/confirm', {
    user_id:       userId,
    season_id:     seasonId,
    amount_staked: amountStaked,
    tx_hash:       txHash,
  }).then(r => r.data)

// ── Game ───────────────────────────────────────────────────────────────────────
export const startGame = (userId) =>
  api.post('/game/start', { user_id: userId }).then(r => r.data)

export const submitGuess = (userId, guess) =>
  api.post('/game/guess', { user_id: userId, guess }).then(r => r.data)

export const getGameState = (userId) =>
  api.get(`/game/state/${userId}`).then(r => r.data)

// ── Leaderboard ────────────────────────────────────────────────────────────────
export const getLeaderboard = (seasonId) =>
  api.get(`/leaderboard/${seasonId}`).then(r => r.data)

export const getSeasonProgress = (seasonId, userId) =>
  api.get(`/leaderboard/progress/${seasonId}/${userId}`).then(r => r.data)