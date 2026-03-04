"""
YieldPlay Real Client — gọi trực tiếp YieldPlay API server.

Interface GIỐNG HỆT yieldplay_mock.py — seasons.py không cần thay đổi.

Khi switch từ mock sang real:
    .env: YIELDPLAY_USE_MOCK=false
    Đảm bảo YIELDPLAY_BASE_URL, YIELDPLAY_API_KEY, YIELDPLAY_GAME_ID đã set.

Endpoints ánh xạ:
    create_game()          → POST /games
    create_round()         → POST /games/{game_id}/rounds
    approve_token()        → POST /users/approve
    deposit()              → POST /users/deposit
    claim()                → POST /users/claim
    deposit_to_vault()     → POST /rounds/vault/deposit
    withdraw_from_vault()  → POST /rounds/vault/withdraw
    settlement()           → POST /rounds/settlement
    choose_winner()        → POST /rounds/winner
    finalize_round()       → POST /rounds/finalize
    get_fee_preview()      → GET  /rounds/{game_id}/{round_id}/fee-preview
    calculate_prize_pool() → local arithmetic (giống mock)
"""

from __future__ import annotations

from decimal import Decimal

import httpx

from config import settings
from services.types import (
    CreateGameResponse,
    CreateRoundResponse,
    FeeBreakdown,
    TransactionResult,
)

PERFORMANCE_FEE_BPS: int = 2000
MOCK_APY: float = 0.045
SEASON_DAYS: int = 30
DECIMALS: int = 6
TOP3_WEIGHTS: list[float] = [0.50, 0.30, 0.20]


# ── HTTP client ────────────────────────────────────────────────────────────────


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.YIELDPLAY_API_KEY}",
        "Content-Type": "application/json",
    }


async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{settings.YIELDPLAY_BASE_URL}{path}",
            json=body,
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{settings.YIELDPLAY_BASE_URL}{path}",
            params=params,
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _to_wei(amount: float) -> int:
    return int(Decimal(str(amount)) * Decimal(10**DECIMALS))


def _from_wei(amount_wei: int) -> float:
    return float(Decimal(str(amount_wei)) / Decimal(10**DECIMALS))


def _tx(data: dict) -> TransactionResult:
    return TransactionResult(
        tx_hash=data.get("tx_hash") or data.get("transaction", {}).get("tx_hash"),
        success=data.get("success", True),
        message=data.get("message", ""),
    )


# ── Fee calculation (local, không cần API call) ────────────────────────────────


def calculate_prize_pool(
    total_deposited: float,
    dev_fee_bps: int = 1000,
    deposit_fee_bps: int = 0,
) -> FeeBreakdown:
    """
    Arithmetic thuần — không cần gọi API.
    Giống mock, dùng để estimate prize pool realtime.

    prize_pool = yield_to_pool + deposit_fee
    """
    yield_amount = total_deposited * MOCK_APY * (SEASON_DAYS / 365)
    perf_fee = yield_amount * (PERFORMANCE_FEE_BPS / 10000)
    net_yield = yield_amount - perf_fee
    dev_fee = net_yield * (dev_fee_bps / 10000)
    yield_to_pool = net_yield - dev_fee
    deposit_fee = total_deposited * (deposit_fee_bps / 10000)
    prize_pool = yield_to_pool + deposit_fee

    return FeeBreakdown(
        total_yield_wei=_to_wei(yield_amount),
        performance_fee_wei=_to_wei(perf_fee),
        dev_fee_wei=_to_wei(dev_fee),
        deposit_fee_wei=_to_wei(deposit_fee),
        prize_pool_wei=_to_wei(prize_pool),
        total_yield_formatted=round(yield_amount, 6),
        deposit_fee_formatted=round(deposit_fee, 6),
        prize_pool_formatted=round(prize_pool, 6),
    )


# ── 1. POST /games ─────────────────────────────────────────────────────────────


async def create_game(
    game_name: str,
    dev_fee_bps: int = 1000,
    treasury: str = "0x0000000000000000000000000000000000000000",
) -> CreateGameResponse:
    data = await _post(
        "/games",
        {
            "game_name": game_name,
            "dev_fee_bps": dev_fee_bps,
            "treasury": treasury,
        },
    )
    return CreateGameResponse(
        game_id=data["game_id"],
        transaction=_tx(data.get("transaction", {})),
    )


# ── 2. POST /games/{game_id}/rounds ───────────────────────────────────────────


async def create_round(
    game_id: str,
    start_ts: int,
    end_ts: int,
    lock_time: int = 43200,
    deposit_fee_bps: int = 0,
) -> CreateRoundResponse:
    data = await _post(
        f"/games/{game_id}/rounds",
        {
            "game_id": game_id,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "lock_time": lock_time,
            "deposit_fee_bps": deposit_fee_bps,
        },
    )
    return CreateRoundResponse(
        round_id=data["round_id"],
        transaction=_tx(data.get("transaction", {})),
    )


# ── 3. POST /users/approve ────────────────────────────────────────────────────


async def approve_token(
    user_wallet: str,
    token_address: str,
    amount_wei: int | None = None,
) -> TransactionResult:
    body: dict = {"token_address": token_address}
    if amount_wei is not None:
        body["amount_wei"] = str(amount_wei)
    return _tx(await _post("/users/approve", body))


# ── 4. POST /users/deposit ────────────────────────────────────────────────────


async def deposit(
    user_wallet: str,
    game_id: str,
    round_id: int,
    amount_wei: int,
) -> TransactionResult:
    return _tx(
        await _post(
            "/users/deposit",
            {
                "game_id": game_id,
                "round_id": round_id,
                "amount_wei": str(amount_wei),
            },
        )
    )


# ── 5. POST /users/claim ──────────────────────────────────────────────────────


async def claim(
    user_wallet: str,
    game_id: str,
    round_id: int,
) -> TransactionResult:
    return _tx(
        await _post(
            "/users/claim",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


# ── 6. POST /rounds/vault/deposit ─────────────────────────────────────────────


async def deposit_to_vault(game_id: str, round_id: int) -> TransactionResult:
    return _tx(
        await _post(
            "/rounds/vault/deposit",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


# ── 7. POST /rounds/vault/withdraw ────────────────────────────────────────────


async def withdraw_from_vault(game_id: str, round_id: int) -> TransactionResult:
    return _tx(
        await _post(
            "/rounds/vault/withdraw",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


# ── 8. POST /rounds/settlement ────────────────────────────────────────────────


async def settlement(game_id: str, round_id: int) -> TransactionResult:
    return _tx(
        await _post(
            "/rounds/settlement",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


# ── 9. POST /rounds/winner ────────────────────────────────────────────────────


async def choose_winner(
    game_id: str,
    round_id: int,
    winner_address: str,
    amount_wei: int,
) -> TransactionResult:
    return _tx(
        await _post(
            "/rounds/winner",
            {
                "game_id": game_id,
                "round_id": round_id,
                "winner": winner_address,
                "amount_wei": str(amount_wei),
            },
        )
    )


# ── 10. POST /rounds/finalize ─────────────────────────────────────────────────


async def finalize_round(game_id: str, round_id: int) -> TransactionResult:
    return _tx(
        await _post(
            "/rounds/finalize",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


# ── 11. GET /rounds/{game_id}/{round_id}/fee-preview ──────────────────────────


async def get_fee_preview(
    game_id: str,
    round_id: int,
    total_deposited: float,
    dev_fee_bps: int = 1000,
) -> FeeBreakdown:
    """
    Gọi API để lấy fee preview chính xác từ on-chain state.
    Fallback về local calculation nếu API fail.
    """
    try:
        data = await _get(
            f"/rounds/{game_id}/{round_id}/fee-preview",
            params={"yield_wei": _to_wei(total_deposited * MOCK_APY * SEASON_DAYS / 365)},
        )
        return FeeBreakdown(
            total_yield_wei=int(data.get("total_yield_wei", 0)),
            performance_fee_wei=int(data.get("performance_fee_wei", 0)),
            dev_fee_wei=int(data.get("dev_fee_wei", 0)),
            deposit_fee_wei=int(data.get("deposit_fee_wei", 0)),
            prize_pool_wei=int(data.get("prize_pool_wei", 0)),
            total_yield_formatted=float(data.get("total_yield_formatted", 0)),
            deposit_fee_formatted=float(data.get("deposit_fee_formatted", 0)),
            prize_pool_formatted=float(data.get("prize_pool_formatted", 0)),
        )
    except Exception:
        return calculate_prize_pool(total_deposited, dev_fee_bps)
