import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Users ──────────────────────────────────────────────
export const createUser = (username, walletAddress) =>
  api.post('/users', { username, wallet_address: walletAddress }).then(r => r.data)

export const getUser = (userId) =>
  api.get(`/users/${userId}`).then(r => r.data)

// ── Seasons ────────────────────────────────────────────
export const getActiveSeason = () =>
  api.get('/seasons/active').then(r => r.data)

export const joinSeason = (userId, seasonId, amountStaked) =>
  api.post('/seasons/join', {
    user_id: userId,
    season_id: seasonId,
    amount_staked: amountStaked,
  }).then(r => r.data)

// ── Game ───────────────────────────────────────────────
export const startGame = (userId) =>
  api.post('/game/start', { user_id: userId }).then(r => r.data)

export const submitGuess = (userId, guess) =>
  api.post('/game/guess', { user_id: userId, guess }).then(r => r.data)

export const getGameState = (userId) =>
  api.get(`/game/state/${userId}`).then(r => r.data)

// ── Leaderboard ────────────────────────────────────────
export const getLeaderboard = (seasonId) =>
  api.get(`/leaderboard/${seasonId}`).then(r => r.data)

export const getSeasonProgress = (seasonId, userId) =>
  api.get(`/leaderboard/progress/${seasonId}/${userId}`).then(r => r.data)

export const getUserByWallet = (walletAddress) =>
  api.get('/users', { params: { wallet_address: walletAddress } }).then(r => r.data)

export const checkParticipation = (seasonId, userId) =>
  api.get(`/seasons/check/${seasonId}/${userId}`).then(r => r.data)
