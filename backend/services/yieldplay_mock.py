"""
YieldPlay Real Client — gọi trực tiếp YieldPlay API server.

Architecture non-custodial
──────────────────────────
Server giữ private key của GAME OWNER → ký các tx quản lý game.
User giữ private key của chính họ    → frontend tự ký deposit/claim.

                    Backend (file này)          Frontend
                    ──────────────────          ────────
create_game()       POST /games                 –
create_round()      POST /games/{id}/rounds     –
deposit_to_vault()  POST /rounds/vault/deposit  –
withdraw_from_vault POST /rounds/vault/withdraw –
settlement()        POST /rounds/settlement     –
choose_winner()     POST /rounds/winner         –
finalize_round()    POST /rounds/finalize       –
                                                POST /tx/build/approve
approve_token()     [REMOVED — frontend only]   POST /tx/build/deposit
deposit()           [REMOVED — frontend only]   POST /tx/build/claim
claim()             [REMOVED — frontend only]   POST /tx/broadcast
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
    UnsignedTxResponse,
)

PERFORMANCE_FEE_BPS: int = 2_000
MOCK_APY: float = 0.045
SEASON_DAYS: int = 30
DECIMALS: int = 6
TOP3_WEIGHTS: list[float] = [0.50, 0.30, 0.20]


# ── HTTP helpers ───────────────────────────────────────────────────────────────


def _headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
    }

    api_key = settings.YIELDPLAY_API_KEY
    if api_key:
        # Không dùng Bearer, gửi raw key
        headers["Authorization"] = api_key

    return headers


async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{settings.YIELDPLAY_BASE_URL}{settings.YIELDPLAY_API_PREFIX}{path}",
            json=body,
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{settings.YIELDPLAY_BASE_URL}{settings.YIELDPLAY_API_PREFIX}{path}",
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
    """Parse TransactionResult from any API response shape."""
    tx = data.get("transaction") or data
    return TransactionResult(
        tx_hash=tx.get("tx_hash", ""),
        success=tx.get("status", 1) == 1,
        message=data.get("message", ""),
    )


# ── Fee calculation (local, không cần API call) ────────────────────────────────


def calculate_prize_pool(
    total_deposited: float,
    dev_fee_bps: int = 1_000,
    deposit_fee_bps: int = 0,
) -> FeeBreakdown:
    """
    Arithmetic thuần — không cần gọi API.
    Dùng để estimate prize pool realtime trên UI.
    """
    yield_amount = total_deposited * MOCK_APY * (SEASON_DAYS / 365)
    perf_fee = yield_amount * (PERFORMANCE_FEE_BPS / 10_000)
    net_yield = yield_amount - perf_fee
    dev_fee = net_yield * (dev_fee_bps / 10_000)
    yield_to_pool = net_yield - dev_fee
    deposit_fee = total_deposited * (deposit_fee_bps / 10_000)
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


# ══════════════════════════════════════════════════════════════════════════════
# GAME OWNER OPERATIONS — server ký bằng YIELDPLAY_PRIVATE_KEY
# ══════════════════════════════════════════════════════════════════════════════


async def create_game(
    game_name: str,
    dev_fee_bps: int = 1_000,
    treasury: str = settings.GAME_TREASURY_ADDRESS,
) -> CreateGameResponse:
    """Tạo game mới. Server ký bằng game owner key."""
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
        transaction=_tx(data),
    )


async def create_round(
    game_id: str,
    start_ts: int,
    end_ts: int,
    lock_time: int = 43_200,  # 12 hours
    deposit_fee_bps: int = 0,
    payment_token: str = settings.YIELDPLAY_TOKEN_ADDRESS,
) -> CreateRoundResponse:
    """Tạo round mới. Server ký bằng game owner key."""
    data = await _post(
        f"/games/{game_id}/rounds",
        {
            "game_id": game_id,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "lock_time": lock_time,
            "deposit_fee_bps": deposit_fee_bps,
            "payment_token": payment_token,
        },
    )
    return CreateRoundResponse(
        round_id=data["round_id"],
        transaction=_tx(data),
    )


async def deposit_to_vault(game_id: str, round_id: int) -> TransactionResult:
    """Deploy funds vào vault. Server ký bằng game owner key."""
    return _tx(
        await _post(
            "/rounds/vault/deposit",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


async def withdraw_from_vault(game_id: str, round_id: int) -> TransactionResult:
    """Rút funds từ vault. Server ký bằng game owner key."""
    return _tx(
        await _post(
            "/rounds/vault/withdraw",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


async def settlement(game_id: str, round_id: int) -> TransactionResult:
    """Phân phối phí. Server ký bằng game owner key."""
    return _tx(
        await _post(
            "/rounds/settlement",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


async def choose_winner(
    game_id: str,
    round_id: int,
    winner_address: str,
    amount_wei: int,
) -> TransactionResult:
    """Chọn winner. Server ký bằng game owner key."""
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


async def finalize_round(game_id: str, round_id: int) -> TransactionResult:
    """Finalize round, mở cửa sổ claim. Server ký bằng game owner key."""
    return _tx(
        await _post(
            "/rounds/finalize",
            {
                "game_id": game_id,
                "round_id": round_id,
            },
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# USER OPERATIONS — non-custodial, frontend ký
#
# Các hàm dưới đây trả về UnsignedTxResponse để frontend ký.
# Gọi từ API endpoint của game server rồi trả về cho frontend.
#
# Flow:
#   1. Frontend gọi game server API endpoint
#   2. Game server gọi build_*() bên dưới → nhận unsigned tx
#   3. Game server trả unsigned tx cho frontend
#   4. Frontend ký bằng MetaMask / WalletConnect
#   5. Frontend gọi broadcast_tx() để push lên chain
# ══════════════════════════════════════════════════════════════════════════════


async def build_approve_tx(
    user_wallet: str,
    token_address: str,
    amount_wei: int | None = None,
) -> UnsignedTxResponse:
    """
    Build unsigned approve tx cho user ký.
    amount_wei=None → approve MaxUint256 (unlimited).
    """
    body: dict = {
        "from_address": user_wallet,
        "token_address": token_address,
    }
    if amount_wei is not None:
        body["amount_wei"] = str(amount_wei)
    return UnsignedTxResponse(**(await _post("/tx/build/approve", body)))


async def build_deposit_tx(
    user_wallet: str,
    game_id: str,
    round_id: int,
    amount_wei: int,
) -> UnsignedTxResponse:
    """
    Build unsigned deposit tx cho user ký.
    Validates round status + balance trước khi build — raise HTTPError nếu invalid.
    """
    return UnsignedTxResponse(
        **(
            await _post(
                "/tx/build/deposit",
                {
                    "from_address": user_wallet,
                    "game_id": game_id,
                    "round_id": round_id,
                    "amount_wei": str(amount_wei),
                },
            )
        )
    )


async def build_claim_tx(
    user_wallet: str,
    game_id: str,
    round_id: int,
) -> UnsignedTxResponse:
    """Build unsigned claim tx cho user ký."""
    return UnsignedTxResponse(
        **(
            await _post(
                "/tx/build/claim",
                {
                    "from_address": user_wallet,
                    "game_id": game_id,
                    "round_id": round_id,
                },
            )
        )
    )


async def broadcast_tx(signed_tx: str) -> str:
    """
    Push signed tx lên chain. Trả về tx_hash.
    signed_tx: hex string "0x..." từ wallet sau khi ký.
    """
    data = await _post("/tx/broadcast", {"signed_tx": signed_tx})
    return data["tx_hash"]


# ── Fee preview ────────────────────────────────────────────────────────────────


async def get_fee_preview(
    game_id: str,
    round_id: int,
    total_deposited: float,
    dev_fee_bps: int = 1_000,
) -> FeeBreakdown:
    """
    Lấy fee preview từ on-chain state.
    Fallback về local calculation nếu API fail.
    """
    try:
        data = await _get(
            f"/rounds/{game_id}/{round_id}/fee-preview",
            params={"yield_wei": _to_wei(total_deposited * MOCK_APY * SEASON_DAYS / 365)},
        )
        return FeeBreakdown(
            total_yield_wei=int(data.get("vault_yield", 0)),
            performance_fee_wei=int(data.get("performance_fee", 0)),
            dev_fee_wei=int(data.get("dev_fee", 0)),
            deposit_fee_wei=int(data.get("deposit_fee_collected", 0)),
            prize_pool_wei=int(data.get("total_prize_pool", 0)),
            total_yield_formatted=_from_wei(int(data.get("vault_yield", 0))),
            deposit_fee_formatted=_from_wei(int(data.get("deposit_fee_collected", 0))),
            prize_pool_formatted=_from_wei(int(data.get("total_prize_pool", 0))),
        )
    except Exception:
        return calculate_prize_pool(total_deposited, dev_fee_bps)


# ── REMOVED — đã chuyển sang non-custodial ────────────────────────────────────
#
# approve_token(user_wallet, token_address, amount_wei)
#   → Thay bằng: build_approve_tx() + frontend ký + broadcast_tx()
#
# deposit(user_wallet, game_id, round_id, amount_wei)
#   → Thay bằng: build_deposit_tx() + frontend ký + broadcast_tx()
#
# claim(user_wallet, game_id, round_id)
#   → Thay bằng: build_claim_tx() + frontend ký + broadcast_tx()
