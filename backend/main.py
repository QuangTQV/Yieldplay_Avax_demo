from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

import models  # noqa: F401
from config import settings
from database import AsyncSessionLocal, Base, engine
from models import Season
from routers import game, leaderboard, seasons, users
from services.yieldplay_mock import create_game, create_round


async def _seed_if_empty() -> None:
    """
    Khi khởi động lần đầu (DB trống):
    1. Tạo YieldPlay Game (1 lần duy nhất) → lưu game_id vào settings
    2. Tạo Season 1 với Round tương ứng
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Season).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        # Tạo game nếu chưa có game_id trong config
        game_id = settings.YIELDPLAY_GAME_ID
        if not game_id:
            game_response = await create_game(
                game_name="WordlePlay",
                dev_fee_bps=1000,
                treasury="0x0000000000000000000000000000000000000000",
            )
            game_id = game_response.game_id
            print(f"[startup] YieldPlay Game created. game_id={game_id}")
            print(f"[startup] Add to .env: YIELDPLAY_GAME_ID={game_id}")

        # Tạo round cho Season 1
        start_date = date.today()
        end_date = start_date + timedelta(days=30)

        def to_ts(d: date) -> int:
            return int(
                datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp()
            )

        round_response = await create_round(
            game_id=game_id,
            start_ts=to_ts(start_date),
            end_ts=to_ts(end_date),
            lock_time=43200,
        )

        season = Season(
            name="Season 1",
            start_date=start_date,
            end_date=end_date,
            status="active",
            dev_fee_bps=5000,
            yieldplay_game_id=game_id,
            yieldplay_round_id=round_response.round_id,
        )
        db.add(season)
        await db.commit()
        print(f"[startup] Season 1 created. round_id={round_response.round_id}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_if_empty()
    yield
    await engine.dispose()


app = FastAPI(title="YieldPlay Wordle API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(seasons.router)
app.include_router(game.router)
app.include_router(leaderboard.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "YieldPlay Wordle API"}
