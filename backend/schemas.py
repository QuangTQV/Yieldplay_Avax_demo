from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Re-export LetterEval từ service types để API layer dùng chung một model
from services.types import LetterEval

SeasonStatus = Literal["active", "ended"]


# ── User ──────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    wallet_address: str = Field(..., min_length=10, max_length=100)


class UserOut(BaseModel):
    id: UUID
    username: str
    wallet_address: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Season ────────────────────────────────────────────────────────────────────


class SeasonCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    start_date: date
    end_date: date
    lock_time: int = Field(..., gt=0)  # seconds before round end when deposits are locked
    dev_fee_bps: int = Field(..., ge=0, le=10000)  # basis points, e.g. 1000 = 10%


class SeasonOut(BaseModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    status: SeasonStatus
    total_deposited: float = 0
    yield_generated: float = 0
    total_reward_pool: float = 0
    yieldplay_game_id: str | None = None
    yieldplay_round_id: int | None = None

    model_config = {"from_attributes": True}


# ── Join Season ───────────────────────────────────────────────────────────────


class JoinSeasonRequest(BaseModel):
    user_id: UUID
    season_id: UUID
    amount_staked: float = Field(..., gt=0)


class JoinSeasonResponse(BaseModel):
    participant_id: UUID
    user_id: UUID
    season_id: UUID
    amount_staked: float
    participation_fee: float


# ── Game ──────────────────────────────────────────────────────────────────────


class StartGameRequest(BaseModel):
    user_id: UUID


class GuessRequest(BaseModel):
    user_id: UUID
    guess: str = Field(..., min_length=5, max_length=5, pattern=r"^[a-zA-Z]+$")


class GuessResponse(BaseModel):
    result: list[LetterEval]
    attempts_used: int
    won: bool
    completed: bool
    score: int | None = None
    answer: str | None = None  # tiết lộ khi game kết thúc và thua


class GameStateResponse(BaseModel):
    play_date: date
    guesses: list[list[LetterEval]]
    attempts_used: int
    completed: bool
    won: bool
    score: int | None = None


# ── Leaderboard ───────────────────────────────────────────────────────────────


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    username: str
    season_score: int
    days_played: int
    days_won: int


class LeaderboardResponse(BaseModel):
    season: SeasonOut
    leaderboard: list[LeaderboardEntry]
    total_players: int
    reward_pool: float


# ── Season Progress ───────────────────────────────────────────────────────────


class DailyScoreEntry(BaseModel):
    play_date: date
    score: int
    won: bool
    attempts_count: int


class SeasonProgressResponse(BaseModel):
    user_id: UUID
    season_id: UUID
    total_score: int
    days_played: int
    days_won: int
    current_rank: int
    total_players: int
    daily_scores: list[DailyScoreEntry]
