"""
Pydantic models cho service layer.
Tách riêng khỏi schemas.py (API layer) để tránh circular import.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Scoring / Word evaluation ──────────────────────────────────────────────────

LetterStatus = Literal["correct", "present", "absent"]


class LetterEval(BaseModel):
    """Kết quả đánh giá một ký tự trong lần đoán."""

    letter: str = Field(..., min_length=1, max_length=1)
    status: LetterStatus


# ── YieldPlay SDK ──────────────────────────────────────────────────────────────


class StakeSplit(BaseModel):
    """Phân chia số tiền stake thành fee và principal."""

    participation_fee: float
    principal: float


class SeasonResult(BaseModel):
    """Một dòng kết quả gửi lên YieldPlay khi kết thúc season."""

    user_id: str
    total_score: int
    rank: int


class YieldPlayDistribution(BaseModel):
    """Phần thưởng phân phối cho một người chơi."""

    rank: int
    user_id: str
    reward_usdc: float


class YieldPlayJoinResponse(BaseModel):
    """Response từ POST /yieldplay/join-season (mock)."""

    success: bool
    yieldplay_participant_id: str
    user_id: str
    wallet_address: str
    amount_staked: float
    participation_fee: float
    principal: float
    staked_at: str
    estimated_yield_apy: str
    message: str


class YieldPlaySubmitResponse(BaseModel):
    """Response từ POST /yieldplay/submit-results (mock)."""

    success: bool
    season_id: str
    yieldplay_job_id: str
    total_reward_pool: float
    base_pool_from_fees: float
    yield_generated: float
    distributions: list[YieldPlayDistribution]
    status: str
    message: str


class YieldPlayPoolStatus(BaseModel):
    """Trạng thái pool hiện tại của một season."""

    season_id: str
    base_pool: float
    yield_accrued: float
    total_pool: float
    participants: int
    apy: str


class EndSeasonResponse(BaseModel):
    """Response trả về từ endpoint kết thúc season."""

    message: str
    yieldplay_response: YieldPlaySubmitResponse


from datetime import datetime

from pydantic import BaseModel, Field


class YieldPlayCreatePoolResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether pool creation succeeded")
    pool_id: str = Field(..., description="Unique identifier of the created pool")
    name: str = Field(..., description="Name of the pool")
    start_time: datetime = Field(..., description="Pool start timestamp (UTC)")
    end_time: datetime = Field(..., description="Pool end timestamp (UTC)")
    status: str = Field(..., description="Current status of the pool (e.g., active)")
    message: str = Field(..., description="Human-readable status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "pool_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Wordle Season 1",
                "start_time": "2026-03-01T00:00:00Z",
                "end_time": "2026-03-30T23:59:59Z",
                "status": "active",
                "message": "pool created. pool_id=550e8400-e29b-41d4-a716-446655440000",
            }
        }
    }
