-- YieldPlay Wordle Season DB Schema

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
    status VARCHAR(20) DEFAULT 'active', -- active | ended
    base_reward_pool DECIMAL(18, 6) DEFAULT 0,
    yield_generated DECIMAL(18, 6) DEFAULT 0,
    total_reward_pool DECIMAL(18, 6) DEFAULT 0,
    yieldplay_pool_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE season_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    season_id UUID REFERENCES seasons(id),
    amount_staked DECIMAL(18, 6) NOT NULL,
    participation_fee DECIMAL(18, 6) NOT NULL,
    principal DECIMAL(18, 6) NOT NULL,
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

CREATE TABLE yieldplay_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(50),               -- join-season | submit-results
    payload JSONB,
    response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_daily_attempts_user_date ON daily_attempts(user_id, play_date);
CREATE INDEX idx_daily_attempts_season ON daily_attempts(season_id);
CREATE INDEX idx_season_participants_season ON season_participants(season_id);

-- Seed active season
INSERT INTO seasons (name, start_date, end_date, status)
VALUES ('Season 1', CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', 'active');

-- Seed daily words (30 days)
-- In production this would be a managed word pool
