-- YieldPlay Wordle Season DB Schema
-- Chain: EVM / Avalanche (Solidity contract)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    wallet_address VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE seasons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',            -- active | ended
    -- YieldPlay contract references
    yieldplay_game_id VARCHAR(100),                 -- bytes32, tạo 1 lần qua POST /games
    yieldplay_round_id INTEGER,                     -- uint256, tạo mỗi season qua POST /games/{id}/rounds
    dev_fee_bps INTEGER DEFAULT 1000,               -- 10% dev fee (% of net yield)
    deposit_fee_bps INTEGER DEFAULT 0,              -- % of each deposit → prize pool
    -- Reward pool (tính từ yield, không phải từ principal)
    total_deposited DECIMAL(18, 6) DEFAULT 0,       -- tổng USDC user đã deposit
    yield_generated DECIMAL(18, 6) DEFAULT 0,       -- yield thu được từ vault
    total_reward_pool DECIMAL(18, 6) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE season_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    season_id UUID REFERENCES seasons(id),
    amount_staked DECIMAL(18, 6) NOT NULL,       -- principal (100% trả lại user)
    deposit_tx_hash VARCHAR(100) NOT NULL,      -- tx hash của deposit vào vault
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, season_id)
);

CREATE TABLE daily_words (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    play_date DATE UNIQUE NOT NULL,
    word VARCHAR(5) NOT NULL,
    season_id UUID REFERENCES seasons(id)
);

CREATE TABLE daily_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    play_date DATE NOT NULL,
    season_id UUID REFERENCES seasons(id),
    guesses JSONB DEFAULT '[]',       -- array of guess strings
    attempts_count INT DEFAULT 0,
    time_seconds INT DEFAULT 0,
    won BOOLEAN DEFAULT FALSE,
    completed BOOLEAN DEFAULT FALSE,
    score INT DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, play_date)
);

-- Indexes
CREATE INDEX idx_daily_attempts_user_date ON daily_attempts(user_id, play_date);
CREATE INDEX idx_daily_attempts_season ON daily_attempts(season_id);
CREATE INDEX idx_season_participants_season ON season_participants(season_id);

-- Seasons được tạo qua POST /seasons (tự động gọi YieldPlay POST /games/{id}/rounds)
-- Game được tạo 1 lần qua POST /games khi deploy, game_id lưu vào config
