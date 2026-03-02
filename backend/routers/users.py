from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from database import get_db
from models import User
from schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


def _validate_evm_address(address: str) -> str:
    """Validate và chuẩn hoá địa chỉ EVM về EIP-55 checksum format."""
    if not Web3.is_address(address):
        raise HTTPException(
            status_code=400,
            detail="Invalid EVM wallet address. Expected: 0x + 40 hex characters.",
        )
    return Web3.to_checksum_address(address)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> UserOut:
    wallet = _validate_evm_address(body.wallet_address)

    dup_username = await db.execute(select(User).where(User.username == body.username))
    if dup_username.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Username already taken")

    dup_wallet = await db.execute(select(User).where(User.wallet_address == wallet))
    if dup_wallet.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Wallet already registered")

    user = User(username=body.username, wallet_address=wallet)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("", response_model=UserOut)
async def get_user_by_wallet(
    wallet_address: str,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Tìm user theo wallet address — dùng khi reconnect MetaMask."""
    wallet = _validate_evm_address(wallet_address)
    result = await db.execute(select(User).where(User.wallet_address == wallet))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)) -> UserOut:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)
