from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import DailyAttempt, Season, User
from schemas import (
    DailyScoreEntry,
    LeaderboardEntry,
    LeaderboardResponse,
    SeasonOut,
    SeasonProgressResponse,
)

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/{season_id}", response_model=LeaderboardResponse)
async def get_leaderboard(
    season_id: str,
    db: AsyncSession = Depends(get_db),
) -> LeaderboardResponse:
    season = await db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=404, detail="Season not found")

    rows = await db.execute(
        select(
            DailyAttempt.user_id,
            User.username,
            func.coalesce(func.sum(DailyAttempt.score), 0).label("season_score"),
            func.count(DailyAttempt.id).label("days_played"),
            func.coalesce(
                func.sum(func.cast(DailyAttempt.won, Integer)),
                0,
            ).label("days_won"),
        )
        .join(User, User.id == DailyAttempt.user_id)
        .where(DailyAttempt.season_id == season_id)
        .group_by(DailyAttempt.user_id, User.username)
        .order_by(func.sum(DailyAttempt.score).desc())
    )

    leaderboard: list[LeaderboardEntry] = [
        LeaderboardEntry(
            rank=i + 1,
            user_id=row.user_id,
            username=row.username,
            season_score=int(row.season_score),
            days_played=int(row.days_played),
            days_won=int(row.days_won),
        )
        for i, row in enumerate(rows.all())
    ]

    return LeaderboardResponse(
        season=SeasonOut.model_validate(season),
        leaderboard=leaderboard,
        total_players=len(leaderboard),
        reward_pool=float(season.total_reward_pool),
    )


@router.get("/progress/{season_id}/{user_id}", response_model=SeasonProgressResponse)
async def get_season_progress(
    season_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> SeasonProgressResponse:
    rows = await db.execute(
        select(DailyAttempt)
        .where(
            DailyAttempt.season_id == season_id,
            DailyAttempt.user_id == user_id,
        )
        .order_by(DailyAttempt.play_date)
    )
    attempts = rows.scalars().all()

    daily_scores: list[DailyScoreEntry] = [
        DailyScoreEntry(
            play_date=a.play_date,
            score=a.score,
            won=a.won,
            attempts_count=a.attempts_count,
        )
        for a in attempts
    ]

    total_score = sum(a.score for a in attempts)
    days_played = sum(1 for a in attempts if a.completed)
    days_won = sum(1 for a in attempts if a.won)

    # Xác định rank hiện tại trong season
    rank_rows = await db.execute(
        select(
            DailyAttempt.user_id,
            func.coalesce(func.sum(DailyAttempt.score), 0).label("season_score"),
        )
        .where(DailyAttempt.season_id == season_id)
        .group_by(DailyAttempt.user_id)
        .order_by(func.sum(DailyAttempt.score).desc())
    )
    all_players = rank_rows.all()

    current_rank = next(
        (i + 1 for i, row in enumerate(all_players) if str(row.user_id) == str(user_id)),
        len(all_players) + 1,
    )

    return SeasonProgressResponse(
        user_id=user_id,  # type: ignore[arg-type]
        season_id=season_id,  # type: ignore[arg-type]
        total_score=total_score,
        days_played=days_played,
        days_won=days_won,
        current_rank=current_rank,
        total_players=len(all_players),
        daily_scores=daily_scores,
    )
