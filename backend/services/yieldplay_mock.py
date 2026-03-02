"""
Mock YieldPlay SDK – simulates the real API calls.
Replace HTTP calls with real endpoint when SDK is live.
"""

import random
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from config import settings
from services.types import (
    SeasonResult,
    StakeSplit,
    YieldPlayCreatePoolResponse,
    YieldPlayDistribution,
    YieldPlayJoinResponse,
    YieldPlayPoolStatus,
    YieldPlaySubmitResponse,
)

PARTICIPATION_FEE_RATIO: float = settings.PARTICIPATION_FEE_RATIO  # 2%
TOP3_WEIGHTS: list[float] = [0.50, 0.30, 0.20]
MOCK_APY: float = 0.045  # 4.5% APY
SEASON_DAYS: int = 30
MOCK_STAKE_PER_USER: float = 10.0  # giả định mỗi user stake 10 USDC


class SerializedTxData(BaseModel):
    """Data containing the base64 transaction string."""

    transaction: str = Field(description="Base64 encoded transaction string")


class SerializedTxResponse(BaseModel):
    """Response wrapper for transaction building endpoints."""

    success: bool = Field(default=True)
    data: SerializedTxData
    trace_id: str = Field(default="tx-builder")


# ── 1. Tạo Pool ────────────────────────────────────────────────────────────────


async def create_pool(
    name: str,
    start_time: int,  # unix timestamp
    end_time: int,  # unix timestamp
) -> YieldPlayCreatePoolResponse:
    """
    Mock POST /pools

    API thật:
        payload = CreateRoundRequest(
            ticket_base_price=int(ticket_base_price * 1_000_000),  # lamport
            ticket_price_jump=int(ticket_price_jump * 1_000_000),
            start_time=start_time,
            end_time=end_time,
        )
        response = await contract_connector_client.create_round(payload)
        pool.round_id = response.data.round_id  # ID on-chain

    Mock: trả về pool_id và round_id giả.
    """
    mock_pool_id = str(uuid.uuid4())

    return YieldPlayCreatePoolResponse(
        success=True,
        pool_id=mock_pool_id,
        name=name,
        start_time=start_time,
        end_time=end_time,
        status="active",
        message=f"pool created. pool_id={mock_pool_id}",
    )


# ----------------------------------------------------


def calculate_stake_split(amount_staked: float) -> StakeSplit:
    """Phân chia số tiền stake thành participation_fee và principal."""
    fee = round(amount_staked * PARTICIPATION_FEE_RATIO, 6)
    principal = round(amount_staked - fee, 6)
    return StakeSplit(participation_fee=fee, principal=principal)


async def join_season(
    user_id: str,
    wallet_address: str,
    amount_staked: float,
) -> YieldPlayJoinResponse:
    """
    Mock POST /yieldplay/join-season
    Trả về YieldPlayJoinResponse với participant ID giả.
    """
    split = calculate_stake_split(amount_staked)
    return YieldPlayJoinResponse(
        success=True,
        yieldplay_participant_id=str(uuid.uuid4()),
        user_id=user_id,
        wallet_address=wallet_address,
        amount_staked=amount_staked,
        participation_fee=split.participation_fee,
        principal=split.principal,
        staked_at=datetime.now(tz=timezone.utc).isoformat(),
        estimated_yield_apy="4.5%",
        message="Successfully joined season. Principal is now generating yield.",
    )


async def submit_results(
    season_id: str,
    results: list[SeasonResult],
) -> YieldPlaySubmitResponse:
    """
    Mock POST /yieldplay/submit-results
    Nhận danh sách SeasonResult, trả về phân phối thưởng.
    """
    total_participants = len(results)
    base_pool = round(total_participants * MOCK_STAKE_PER_USER * PARTICIPATION_FEE_RATIO, 4)
    yield_generated = round(base_pool * MOCK_APY * (SEASON_DAYS / 365), 4)
    total_pool = round(base_pool + yield_generated, 4)

    sorted_results = sorted(results, key=lambda r: r.total_score, reverse=True)
    distributions: list[YieldPlayDistribution] = [
        YieldPlayDistribution(
            rank=i + 1,
            user_id=entry.user_id,
            reward_usdc=round(total_pool * TOP3_WEIGHTS[i], 4),
        )
        for i, entry in enumerate(sorted_results[: len(TOP3_WEIGHTS)])
    ]

    return YieldPlaySubmitResponse(
        success=True,
        season_id=season_id,
        yieldplay_job_id=str(uuid.uuid4()),
        total_reward_pool=total_pool,
        base_pool_from_fees=base_pool,
        yield_generated=yield_generated,
        distributions=distributions,
        status="processing",
        message="Rewards are being distributed on-chain.",
    )


async def get_pool_status(season_id: str) -> YieldPlayPoolStatus:
    """Mock: trả về trạng thái pool hiện tại của một season."""
    base = round(random.uniform(50, 200), 4)
    yield_acc = round(random.uniform(1, 10), 4)
    return YieldPlayPoolStatus(
        season_id=season_id,
        base_pool=base,
        yield_accrued=yield_acc,
        total_pool=round(base + yield_acc, 4),
        participants=random.randint(10, 100),
        apy="4.5%",
    )
