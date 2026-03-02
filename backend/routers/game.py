from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import DailyAttempt, DailyWord, Season, SeasonParticipant, User
from schemas import (
    GameStateResponse,
    GuessRequest,
    GuessResponse,
    StartGameRequest,
)
from services.scoring import MAX_ATTEMPTS, calculate_score, evaluate_guess
from services.types import LetterEval
from services.word_service import get_daily_word_from_seed, is_valid_guess

router = APIRouter(prefix="/game", tags=["game"])


async def _get_today_word(
    today: date,
    season_id: uuid.UUID | None,
    db: AsyncSession,
) -> str:
    """Lấy từ của ngày hôm nay từ DB, nếu chưa có thì seed và lưu vào DB."""
    result = await db.execute(select(DailyWord).where(DailyWord.play_date == today))
    dw = result.scalar_one_or_none()
    if dw is not None:
        return dw.word

    word = get_daily_word_from_seed(today)
    new_dw = DailyWord(play_date=today, word=word, season_id=season_id)
    db.add(new_dw)
    await db.flush()
    return word


def _build_guess_history(guesses: list[str], answer: str) -> list[list[LetterEval]]:
    """Dựng lại lịch sử các lần đoán dưới dạng list[list[LetterEval]]."""
    return [evaluate_guess(g, answer) for g in guesses]


@router.post("/start", response_model=GameStateResponse)
async def start_game(
    body: StartGameRequest,
    db: AsyncSession = Depends(get_db),
) -> GameStateResponse:
    """Lấy hoặc tạo lượt chơi hôm nay của user."""
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()

    season_res = await db.execute(
        select(Season)
        .where(Season.status == "active")
        .order_by(Season.created_at.desc())
    )
    season = season_res.scalar_one_or_none()
    season_id: uuid.UUID | None = season.id if season is not None else None

    if season is not None:
        part_res = await db.execute(
            select(SeasonParticipant).where(
                SeasonParticipant.user_id == body.user_id,
                SeasonParticipant.season_id == season.id,
            )
        )
        if part_res.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="You must join the season before playing")

    word = await _get_today_word(today, season_id, db)

    attempt_res = await db.execute(
        select(DailyAttempt).where(
            DailyAttempt.user_id == body.user_id,
            DailyAttempt.play_date == today,
        )
    )
    attempt = attempt_res.scalar_one_or_none()

    if attempt is None:
        attempt = DailyAttempt(
            user_id=body.user_id,
            play_date=today,
            season_id=season_id,
            guesses=[],
        )
        db.add(attempt)
        await db.flush()

    guesses: list[str] = attempt.guesses or []
    history = _build_guess_history(guesses, word)

    return GameStateResponse(
        play_date=today,
        guesses=history,
        attempts_used=len(guesses),
        completed=attempt.completed,
        won=attempt.won,
        score=attempt.score if attempt.completed else None,
    )


@router.post("/guess", response_model=GuessResponse)
async def submit_guess(
    body: GuessRequest,
    db: AsyncSession = Depends(get_db),
) -> GuessResponse:
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()
    guess = body.guess.lower().strip()

    if not is_valid_guess(guess):
        raise HTTPException(status_code=400, detail="Not a valid word")

    season_res = await db.execute(
        select(Season)
        .where(Season.status == "active")
        .order_by(Season.created_at.desc())
    )
    season = season_res.scalar_one_or_none()
    season_id: uuid.UUID | None = season.id if season is not None else None

    word = await _get_today_word(today, season_id, db)

    attempt_res = await db.execute(
        select(DailyAttempt).where(
            DailyAttempt.user_id == body.user_id,
            DailyAttempt.play_date == today,
        )
    )
    attempt = attempt_res.scalar_one_or_none()

    if attempt is None:
        raise HTTPException(status_code=400, detail="Start the game first")
    if attempt.completed:
        raise HTTPException(status_code=400, detail="You already completed today's puzzle")

    guesses: list[str] = list(attempt.guesses or [])
    if len(guesses) >= MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="No attempts remaining")

    guesses.append(guess)
    attempt.guesses = guesses
    attempt.attempts_count = len(guesses)

    won = guess == word
    time_elapsed = int(
        (datetime.now(tz=timezone.utc) - attempt.started_at.replace(tzinfo=timezone.utc)).total_seconds()
    )
    completed = won or len(guesses) >= MAX_ATTEMPTS

    if completed:
        attempt.won = won
        attempt.completed = True
        attempt.time_seconds = time_elapsed
        attempt.finished_at = datetime.now(tz=timezone.utc)
        attempt.score = calculate_score(len(guesses), time_elapsed, won)

    letter_evals: list[LetterEval] = evaluate_guess(guess, word)

    return GuessResponse(
        result=letter_evals,
        attempts_used=len(guesses),
        won=won,
        completed=completed,
        score=attempt.score if completed else None,
        answer=word if (completed and not won) else None,
    )


@router.get("/state/{user_id}", response_model=GameStateResponse)
async def get_game_state(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> GameStateResponse:
    today = date.today()

    season_res = await db.execute(
        select(Season)
        .where(Season.status == "active")
        .order_by(Season.created_at.desc())
    )
    season = season_res.scalar_one_or_none()
    season_id: uuid.UUID | None = season.id if season is not None else None

    word = await _get_today_word(today, season_id, db)

    attempt_res = await db.execute(
        select(DailyAttempt).where(
            DailyAttempt.user_id == user_id,
            DailyAttempt.play_date == today,
        )
    )
    attempt = attempt_res.scalar_one_or_none()

    if attempt is None:
        return GameStateResponse(
            play_date=today,
            guesses=[],
            attempts_used=0,
            completed=False,
            won=False,
        )

    guesses: list[str] = attempt.guesses or []
    history = _build_guess_history(guesses, word)

    return GameStateResponse(
        play_date=today,
        guesses=history,
        attempts_used=len(guesses),
        completed=attempt.completed,
        won=attempt.won,
        score=attempt.score if attempt.completed else None,
    )
