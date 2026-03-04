"""
Pydantic models cho service layer.
Aligned với YieldPlay SDK (Solidity/EVM).
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ── Word evaluation ────────────────────────────────────────────────────────────

LetterStatus = Literal["correct", "present", "absent"]

class LetterEval(BaseModel):
    letter: str = Field(..., min_length=1, max_length=1)
    status: LetterStatus


# ── Game types ─────────────────────────────────────────────────────────────────

class SeasonResult(BaseModel):
    """Score của một user cuối season — dùng để tính winner."""
    user_id: str
    wallet_address: str
    total_score: int
    rank: int


# ── YieldPlay SDK types ────────────────────────────────────────────────────────

class TransactionResult(BaseModel):
    """
    Response từ mọi write endpoint của SDK.
    tx_hash = None khi mock.
    """
    tx_hash: str | None = None
    success: bool = True
    message: str = ""


class CreateGameResponse(BaseModel):
    """Response từ POST /games."""
    game_id: str        # bytes32 hex
    transaction: TransactionResult


class CreateRoundResponse(BaseModel):
    """Response từ POST /games/{game_id}/rounds."""
    round_id: int       # uint256
    transaction: TransactionResult


class FeeBreakdown(BaseModel):
    """
    Phân tích fee từ GET /rounds/{game_id}/{round_id}/fee-preview.
    User KHÔNG mất principal — prize pool hoàn toàn từ yield.
    """
    total_yield_wei: int = 0
    performance_fee_wei: int = 0      # 20% → protocol treasury
    dev_fee_wei: int = 0              # X% → game treasury
    prize_pool_wei: int = 0           # phần còn lại → winners
    total_yield_formatted: float = 0.0
    prize_pool_formatted: float = 0.0


class WinnerEntry(BaseModel):
    """Một winner được game owner chọn."""
    rank: int
    user_id: str
    wallet_address: str
    prize_wei: int
    prize_formatted: float
    tx_hash: str | None = None


class EndSeasonResponse(BaseModel):
    """Response từ POST /seasons/{id}/end."""
    message: str
    game_id: str
    round_id: int
    winners: list[WinnerEntry]
    prize_pool_formatted: float
    yield_generated_formatted: float
