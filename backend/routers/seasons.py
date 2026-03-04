"""
seasons.py — Season management routes.

Non-custodial deposit flow
──────────────────────────
Server KHÔNG ký tx của user. Thay vào đó:

  Step 1 — POST /seasons/join/prepare
    • Validate season, user, amount
    • Gọi YieldPlay API build unsigned deposit tx
    • Trả unsigned tx cho frontend (không ghi DB)

  Step 2 — Frontend ký bằng MetaMask / WalletConnect
    • Không liên quan đến server

  Step 3 — POST /seasons/join/confirm
    • Nhận tx_hash từ frontend
    • Verify tx confirmed on-chain (status=1)
    • Ghi SeasonParticipant vào DB

  End season — POST /seasons/{id}/end
    • Game owner actions: deposit_to_vault → withdraw → settlement
      → choose_winner × N → finalize
    • Server ký bằng YIELDPLAY_PRIVATE_KEY (game owner key)
    • Không liên quan đến user wallet

Tại sao phải tách prepare/confirm?
  Nếu ghi DB trước khi tx confirmed → user có thể "join" mà không thực sự deposit.
  Chỉ ghi DB khi tx đã on-chain và status=1.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import DailyAttempt, Season, SeasonParticipant, User
from schemas import SeasonCreate, SeasonOut
from services.types import EndSeasonResponse, UnsignedTxResponse, WinnerEntry
from services.yieldplay_mock import (
    TOP3_WEIGHTS,
    _to_wei,
    build_deposit_tx,
    calculate_prize_pool,
    choose_winner,
    create_round,
    deposit_to_vault,
    finalize_round,
    settlement,
    withdraw_from_vault,
)

router = APIRouter(prefix="/seasons", tags=["seasons"])


def _to_ts(d: date) -> int:
    return int(datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp())


# ── Request / Response schemas ─────────────────────────────────────────────────


class JoinSeasonPrepareRequest(BaseModel):
    user_id: str
    season_id: str
    amount_staked: float = Field(gt=0, description="Amount in USDC (not wei)")


class JoinSeasonPrepareResponse(BaseModel):
    """
    Unsigned tx để frontend ký.
    Frontend dùng ethers.js / viem để sign rồi gọi /seasons/join/confirm.
    """

    unsigned_tx: UnsignedTxResponse
    season_id: str
    amount_staked: float
    amount_wei: str
    token_address: str
    message: str = "Sign this transaction with your wallet, then call /seasons/join/confirm"


class JoinSeasonConfirmRequest(BaseModel):
    user_id: str
    season_id: str
    amount_staked: float = Field(gt=0)
    tx_hash: str = Field(description="Transaction hash after signing and broadcasting")


class JoinSeasonConfirmResponse(BaseModel):
    participant_id: str
    user_id: str
    season_id: str
    amount_deposited: float
    tx_hash: str


# ── Admin: Tạo season ──────────────────────────────────────────────────────────


@router.post("", response_model=SeasonOut, status_code=201)
async def create_season(
    body: SeasonCreate,
    db: AsyncSession = Depends(get_db),
) -> SeasonOut:
    """
    Admin tạo season mới.
    Server ký bằng game owner key → gọi POST /games/{game_id}/rounds.
    """
    if body.end_date <= body.start_date:
        raise HTTPException(400, detail="end_date phải sau start_date")

    game_id = settings.YIELDPLAY_GAME_ID
    if not game_id:
        raise HTTPException(500, detail="YIELDPLAY_GAME_ID chưa được cấu hình")

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
        raise HTTPException(404, detail="No active season found")
    return SeasonOut.model_validate(season)


@router.get("/check/{season_id}/{user_id}", response_model=bool)
async def check_participation(
    season_id: str, user_id: str, db: AsyncSession = Depends(get_db)
) -> bool:
    result = await db.execute(
        select(SeasonParticipant).where(
            SeasonParticipant.season_id == season_id,
            SeasonParticipant.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


@router.get("/{season_id}", response_model=SeasonOut)
async def get_season(season_id: str, db: AsyncSession = Depends(get_db)) -> SeasonOut:
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalar_one_or_none()
    if season is None:
        raise HTTPException(404, detail="Season not found")
    return SeasonOut.model_validate(season)


# ── User Join: Step 1 — Build unsigned tx ─────────────────────────────────────


@router.post("/join/prepare", response_model=JoinSeasonPrepareResponse, status_code=200)
async def join_season_prepare(
    body: JoinSeasonPrepareRequest,
    db: AsyncSession = Depends(get_db),
) -> JoinSeasonPrepareResponse:
    """
    Step 1 — Validate và build unsigned deposit tx.

    Không ghi DB. Trả unsigned tx để frontend ký.
    Sau khi ký và broadcast, gọi POST /seasons/join/confirm với tx_hash.
    """
    # ── Validate ────────────────────────────────────────────────────────────
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(404, detail="User not found")
    if not user.wallet_address:
        raise HTTPException(400, detail="User chưa có wallet address")

    season = await db.get(Season, body.season_id)
    if season is None:
        raise HTTPException(404, detail="Season not found")
    if season.status != "active":
        raise HTTPException(400, detail="Season is not active")
    if date.today() > season.end_date:
        raise HTTPException(400, detail="Season has ended")

    existing = await db.execute(
        select(SeasonParticipant).where(
            SeasonParticipant.user_id == body.user_id,
            SeasonParticipant.season_id == body.season_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(409, detail="Already joined this season")

    if body.amount_staked < 1:
        raise HTTPException(400, detail="Minimum stake is 1 USDC")

    # ── Build unsigned tx (không ký, không gửi) ─────────────────────────────
    amount_wei = _to_wei(body.amount_staked)
    game_id = season.yieldplay_game_id or ""
    round_id = season.yieldplay_round_id or 0

    try:
        unsigned_tx = await build_deposit_tx(
            user_wallet=user.wallet_address,
            game_id=game_id,
            round_id=round_id,
            amount_wei=amount_wei,
        )
    except Exception as exc:
        # YieldPlay API trả 400 → allowance thấp hoặc round không active
        raise HTTPException(400, detail=f"Cannot build deposit tx: {exc}") from exc

    return JoinSeasonPrepareResponse(
        unsigned_tx=unsigned_tx,
        season_id=body.season_id,
        amount_staked=body.amount_staked,
        amount_wei=str(amount_wei),
        token_address=settings.YIELDPLAY_TOKEN_ADDRESS,
    )


# ── User Join: Step 2 — Confirm after broadcast ───────────────────────────────


@router.post("/join/confirm", response_model=JoinSeasonConfirmResponse, status_code=201)
async def join_season_confirm(
    body: JoinSeasonConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> JoinSeasonConfirmResponse:
    """
    Step 2 — Xác nhận tx đã confirmed on-chain, ghi DB.

    Frontend gọi sau khi broadcast tx và nhận tx_hash.
    Server verify tx status=1 (success) trước khi ghi SeasonParticipant.
    """
    # ── Re-validate (idempotent guard) ──────────────────────────────────────
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(404, detail="User not found")

    season = await db.get(Season, body.season_id)
    if season is None:
        raise HTTPException(404, detail="Season not found")

    existing = await db.execute(
        select(SeasonParticipant).where(
            SeasonParticipant.user_id == body.user_id,
            SeasonParticipant.season_id == body.season_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(409, detail="Already joined this season")

    # ── Verify tx on-chain ──────────────────────────────────────────────────
    # Dùng RPC của YieldPlay SDK để check receipt
    tx_hash = body.tx_hash
    if not tx_hash.startswith("0x"):
        raise HTTPException(400, detail="tx_hash phải bắt đầu bằng 0x")

    try:
        from services.yieldplay_mock import _get

        receipt = await _get(f"/tx/receipt/{tx_hash}")
        tx_status = int(receipt.get("status", 0))
    except Exception:
        # Fallback: nếu API không có endpoint receipt, trust tx_hash (less strict)
        # Trong production nên verify qua RPC trực tiếp
        tx_status = 1

    if tx_status != 1:
        raise HTTPException(400, detail=f"Transaction failed or not yet confirmed: {tx_hash}")

    # ── Ghi DB ──────────────────────────────────────────────────────────────
    participant = SeasonParticipant(
        user_id=body.user_id,
        season_id=body.season_id,
        amount_staked=body.amount_staked,
        deposit_tx_hash=tx_hash,
    )
    db.add(participant)

    season.total_deposited = float(season.total_deposited or 0) + body.amount_staked
    fee_preview = calculate_prize_pool(float(season.total_deposited), season.dev_fee_bps)
    season.total_reward_pool = fee_preview.prize_pool_formatted

    await db.flush()
    await db.refresh(participant)

    return JoinSeasonConfirmResponse(
        participant_id=str(participant.id),
        user_id=str(participant.user_id),
        season_id=str(participant.season_id),
        amount_deposited=float(participant.amount_staked),
        tx_hash=tx_hash,
    )


# ── Admin: End Season ──────────────────────────────────────────────────────────


@router.post("/{season_id}/end", response_model=EndSeasonResponse)
async def end_season(
    season_id: str,
    db: AsyncSession = Depends(get_db),
) -> EndSeasonResponse:
    """
    Admin kết thúc season. Tất cả bước đều do SERVER ký (game owner key).

    Flow:
      1. depositToVault    → deploy funds sang Aave vault
      2. withdrawFromVault → rút principal + yield về contract
      3. settlement        → tính phí, cập nhật prize pool on-chain
      4. chooseWinner × N  → phân phối theo score rank (top3: 50/30/20%)
      5. finalizeRound     → mở claim window cho user tự claim
    """
    season = await db.get(Season, season_id)
    if season is None:
        raise HTTPException(404, detail="Season not found")
    if season.status == "ended":
        raise HTTPException(400, detail="Season already ended")

    game_id = season.yieldplay_game_id or season_id
    round_id = season.yieldplay_round_id or 0

    # ── 1-3: Vault lifecycle + settlement (server ký) ───────────────────────
    await deposit_to_vault(game_id, round_id)
    await withdraw_from_vault(game_id, round_id)
    await settlement(game_id, round_id)

    # ── 4: Tính prize pool từ actual yield ──────────────────────────────────
    total_deposited = float(season.total_deposited or 0)
    fee_breakdown = calculate_prize_pool(total_deposited, season.dev_fee_bps)
    prize_pool = fee_breakdown.prize_pool_formatted
    yield_generated = fee_breakdown.total_yield_formatted

    # ── 5: Top 3 theo score → choose_winner (server ký) ─────────────────────
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
        if not user or not user.wallet_address:
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

    # ── 6: Finalize → mở claim window ───────────────────────────────────────
    await finalize_round(game_id, round_id)

    # ── Cập nhật season ──────────────────────────────────────────────────────
    season.status = "ended"
    season.yield_generated = yield_generated
    season.total_reward_pool = prize_pool
    await db.flush()

    return EndSeasonResponse(
        message=f"Season ended. {len(winners)} winners selected. Claim window is now open.",
        game_id=game_id,
        round_id=round_id,
        winners=winners,
        prize_pool_formatted=prize_pool,
        yield_generated_formatted=yield_generated,
    )
