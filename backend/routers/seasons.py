from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import DailyAttempt, Season, SeasonParticipant, User
from schemas import JoinSeasonRequest, JoinSeasonResponse, SeasonCreate, SeasonOut
from services.types import EndSeasonResponse, WinnerEntry
from services.yieldplay_mock import (
    TOP3_WEIGHTS,
    _to_wei,
    calculate_prize_pool,
    choose_winner,
    create_round,
    deposit,
    deposit_to_vault,
    finalize_round,
    settlement,
    withdraw_from_vault,
)

router = APIRouter(prefix="/seasons", tags=["seasons"])


def _to_ts(d: date) -> int:
    return int(datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp())


# ── Admin: Tạo season → POST /games/{game_id}/rounds ──────────────────────────


@router.post("", response_model=SeasonOut, status_code=201)
async def create_season(
    body: SeasonCreate,
    db: AsyncSession = Depends(get_db),
) -> SeasonOut:
    """
    Admin tạo season mới.
    Tự động gọi YieldPlay POST /games/{game_id}/rounds để tạo round on-chain.
    game_id đọc từ settings (tạo 1 lần khi deploy game).
    """
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="end_date phải sau start_date")

    game_id = settings.YIELDPLAY_GAME_ID
    if not game_id:
        raise HTTPException(status_code=500, detail="YIELDPLAY_GAME_ID chưa được cấu hình")

    round_response = await create_round(
        game_id=game_id,
        start_ts=_to_ts(body.start_date),
        end_ts=_to_ts(body.end_date),
        lock_time=body.lock_time,
        deposit_fee_bps=0,
    )

    season = Season(
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        status="active",
        dev_fee_bps=body.dev_fee_bps,
        yieldplay_game_id=game_id,
        yieldplay_round_id=round_response.round_id,
    )
    db.add(season)
    await db.flush()
    await db.refresh(season)
    return SeasonOut.model_validate(season)


# ── Get ────────────────────────────────────────────────────────────────────────


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


# ── User Join → POST /users/deposit ───────────────────────────────────────────


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

    # Mock POST /users/deposit
    # API thật: trả TransactionResult → frontend dùng MetaMask để sign & send
    _ = await deposit(
        user_wallet=user.wallet_address,
        game_id=season.yieldplay_game_id or "",
        round_id=season.yieldplay_round_id or 0,
        amount_wei=_to_wei(body.amount_staked),
    )

    participant = SeasonParticipant(
        user_id=body.user_id,
        season_id=body.season_id,
        amount_staked=body.amount_staked,
    )
    db.add(participant)

    # Cập nhật total_deposited và ước tính prize pool
    season.total_deposited = float(season.total_deposited) + body.amount_deposited
    fee_preview = calculate_prize_pool(float(season.total_deposited), season.dev_fee_bps)
    season.total_reward_pool = fee_preview.prize_pool_formatted

    await db.flush()
    await db.refresh(participant)

    return JoinSeasonResponse(
        participant_id=participant.id,
        user_id=participant.user_id,
        season_id=participant.season_id,
        amount_deposited=float(participant.amount_staked),
    )


# ── Admin: End Season ──────────────────────────────────────────────────────────


@router.post("/{season_id}/end", response_model=EndSeasonResponse)
async def end_season(
    season_id: str,
    db: AsyncSession = Depends(get_db),
) -> EndSeasonResponse:
    """
    Admin kết thúc season. Flow theo SDK:
      1. POST /rounds/vault/deposit       → deploy funds sang Aave/Compound
      2. POST /rounds/vault/withdraw      → rút principal + yield về contract
      3. POST /rounds/settlement          → tính fee, cập nhật prize_pool
      4. POST /rounds/winner × N          → phân phối theo score rank
      5. POST /rounds/finalize            → mở claim window

    Wordle mapping: score cao → prize lớn hơn (top3: 50/30/20%)
    """
    season = await db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=404, detail="Season not found")
    if season.status == "ended":
        raise HTTPException(status_code=400, detail="Season already ended")

    game_id = season.yieldplay_game_id or season_id
    round_id = season.yieldplay_round_id or 0

    # ── Bước 1-3: Vault lifecycle + settlement ──
    await deposit_to_vault(game_id, round_id)
    await withdraw_from_vault(game_id, round_id)
    await settlement(game_id, round_id)

    # ── Bước 4: Tính prize pool thật từ yield ──
    total_deposited = float(season.total_deposited or 0)
    fee_breakdown = calculate_prize_pool(total_deposited, season.dev_fee_bps)
    prize_pool = fee_breakdown.prize_pool_formatted
    yield_generated = fee_breakdown.total_yield_formatted

    # ── Bước 5: Lấy top 3 theo score, gọi choose_winner cho từng người ──
    rows = await db.execute(
        select(
            DailyAttempt.user_id,
            func.sum(DailyAttempt.score).label("total_score"),
        )
        .where(DailyAttempt.season_id == season_id)
        .group_by(DailyAttempt.user_id)
        .order_by(func.sum(DailyAttempt.score).desc())
        .limit(3)
    )

    winners: list[WinnerEntry] = []
    for i, row in enumerate(rows.all()):
        user = await db.get(User, row.user_id)
        if not user:
            continue

        prize = round(prize_pool * TOP3_WEIGHTS[i], 6)
        tx = await choose_winner(
            game_id=game_id,
            round_id=round_id,
            winner_address=user.wallet_address,
            amount_wei=_to_wei(prize),
        )
        winners.append(
            WinnerEntry(
                rank=i + 1,
                user_id=str(row.user_id),
                wallet_address=user.wallet_address,
                prize_wei=_to_wei(prize),
                prize_formatted=prize,
                tx_hash=tx.tx_hash,
            )
        )

    # ── Bước 6: Finalize → mở claim window ──
    await finalize_round(game_id, round_id)

    # ── Cập nhật season ──
    season.status = "ended"
    season.yield_generated = yield_generated
    season.prize_pool = prize_pool

    return EndSeasonResponse(
        message=f"Season ended. {len(winners)} winners selected. Claim window is now open.",
        game_id=game_id,
        round_id=round_id,
        winners=winners,
        prize_pool_formatted=prize_pool,
        yield_generated_formatted=yield_generated,
    )
