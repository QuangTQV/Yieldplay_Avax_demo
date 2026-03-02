from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import DailyAttempt, Season, SeasonParticipant, User, YieldPlayLog
from schemas import JoinSeasonRequest, JoinSeasonResponse, SeasonCreate, SeasonOut
from services.types import EndSeasonResponse, SeasonResult
from services.yieldplay_mock import calculate_stake_split, create_pool, join_season, submit_results

router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.post("", response_model=SeasonOut, status_code=201)
async def create_season(
    body: SeasonCreate,
    db: AsyncSession = Depends(get_db),
) -> SeasonOut:
    """
    Admin tạo season mới.
    Tự động gọi YieldPlay POST /pools để tạo pool on-chain.
    """
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="end_date phải sau start_date")

    # Gọi YieldPlay tạo pool trước
    start_ts = int(
        datetime.combine(body.start_date, datetime.min.time())
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )
    end_ts = int(
        datetime.combine(body.end_date, datetime.min.time())
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )

    pool_response = await create_pool(
        name=body.name,
        start_time=start_ts,
        end_time=end_ts,
    )

    if not pool_response.success:
        raise HTTPException(status_code=502, detail="Failed to create YieldPlay pool")

    # Lưu season vào DB với pool_id + round_id từ YieldPlay
    season = Season(
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        status="active",
        yieldplay_pool_id=pool_response.pool_id,
    )
    db.add(season)
    await db.flush()
    await db.refresh(season)
    return SeasonOut.model_validate(season)


@router.get("/active", response_model=SeasonOut)
async def get_active_season(db: AsyncSession = Depends(get_db)) -> SeasonOut:
    result = await db.execute(
        select(Season).where(Season.status == "active").order_by(Season.created_at.desc())
    )
    season = result.scalar_one_or_none()
    if season is None:
        raise HTTPException(status_code=404, detail="No active season found")
    return SeasonOut.model_validate(season)


@router.get("/{season_id}", response_model=SeasonOut)
async def get_season(season_id: str, db: AsyncSession = Depends(get_db)) -> SeasonOut:
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalar_one_or_none()
    if season is None:
        raise HTTPException(status_code=404, detail="Season not found")
    return SeasonOut.model_validate(season)


@router.get("/check/{season_id}/{user_id}", response_model=bool)
async def check_participation(
    season_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Kiểm tra user đã tham gia season chưa."""
    result = await db.execute(
        select(SeasonParticipant).where(
            SeasonParticipant.season_id == season_id,
            SeasonParticipant.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


@router.post("/join", response_model=JoinSeasonResponse, status_code=201)
async def join_season_endpoint(
    body: JoinSeasonRequest,
    db: AsyncSession = Depends(get_db),
) -> JoinSeasonResponse:
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    season = await db.get(Season, body.season_id)
    if season is None:
        raise HTTPException(status_code=404, detail="Season not found")
    if season.status != "active":
        raise HTTPException(status_code=400, detail="Season is not active")
    if date.today() > season.end_date:
        raise HTTPException(status_code=400, detail="Season has ended")

    existing = await db.execute(
        select(SeasonParticipant).where(
            SeasonParticipant.user_id == body.user_id,
            SeasonParticipant.season_id == body.season_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Already joined this season")

    if body.amount_staked < 1:
        raise HTTPException(status_code=400, detail="Minimum stake is 1 USDC")

    # Gọi YieldPlay SDK (mock) – trả về YieldPlayJoinResponse (typed)
    yp_response = await join_season(
        user_id=str(body.user_id),
        wallet_address=user.wallet_address,
        amount_staked=body.amount_staked,
    )

    split = calculate_stake_split(body.amount_staked)

    participant = SeasonParticipant(
        user_id=body.user_id,
        season_id=body.season_id,
        amount_staked=body.amount_staked,
        participation_fee=split.participation_fee,
        principal=split.principal,
    )
    db.add(participant)

    season.base_reward_pool = float(season.base_reward_pool) + split.participation_fee
    season.total_reward_pool = float(season.base_reward_pool) + float(season.yield_generated)

    log = YieldPlayLog(
        action="join-season",
        payload={"user_id": str(body.user_id), "amount_staked": body.amount_staked},
        response=yp_response.model_dump(),
    )
    db.add(log)

    await db.flush()
    await db.refresh(participant)

    return JoinSeasonResponse(
        participant_id=participant.id,
        user_id=participant.user_id,
        season_id=participant.season_id,
        amount_staked=float(participant.amount_staked),
        participation_fee=float(participant.participation_fee),
        principal=float(participant.principal),
    )


@router.post("/{season_id}/end", response_model=EndSeasonResponse)
async def end_season(
    season_id: str,
    db: AsyncSession = Depends(get_db),
) -> EndSeasonResponse:
    """Admin: kết thúc season và gửi kết quả lên YieldPlay."""
    season = await db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=404, detail="Season not found")

    rows = await db.execute(
        select(
            DailyAttempt.user_id,
            func.sum(DailyAttempt.score).label("total_score"),
        )
        .where(DailyAttempt.season_id == season_id)
        .group_by(DailyAttempt.user_id)
        .order_by(func.sum(DailyAttempt.score).desc())
    )

    season_results: list[SeasonResult] = [
        SeasonResult(
            user_id=str(row.user_id),
            total_score=int(row.total_score or 0),
            rank=i + 1,
        )
        for i, row in enumerate(rows.all())
    ]

    yp_response = await submit_results(season_id=str(season.id), results=season_results)

    season.status = "ended"
    season.yield_generated = yp_response.yield_generated
    season.total_reward_pool = yp_response.total_reward_pool

    log = YieldPlayLog(
        action="submit-results",
        payload={"season_id": season_id, "results_count": len(season_results)},
        response=yp_response.model_dump(),
    )
    db.add(log)

    return EndSeasonResponse(message="Season ended", yieldplay_response=yp_response)
