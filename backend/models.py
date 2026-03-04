import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    wallet_address: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    participations: Mapped[list["SeasonParticipant"]] = relationship(back_populates="user")
    attempts: Mapped[list["DailyAttempt"]] = relationship(back_populates="user")


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    total_deposited: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    yield_generated: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    total_reward_pool: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    yieldplay_game_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    yieldplay_round_id: Mapped[int | None] = mapped_column(nullable=True)
    dev_fee_bps: Mapped[int] = mapped_column(default=1000)
    deposit_fee_bps: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    participants: Mapped[list["SeasonParticipant"]] = relationship(back_populates="season")
    daily_words: Mapped[list["DailyWord"]] = relationship(back_populates="season")
    attempts: Mapped[list["DailyAttempt"]] = relationship(back_populates="season")


class SeasonParticipant(Base):
    __tablename__ = "season_participants"
    __table_args__ = (UniqueConstraint("user_id", "season_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    amount_staked: Mapped[float] = mapped_column(Numeric(18, 6))
    participation_fee: Mapped[float] = mapped_column(Numeric(18, 6))
    principal: Mapped[float] = mapped_column(Numeric(18, 6))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship(back_populates="participations")
    season: Mapped["Season"] = relationship(back_populates="participants")


class DailyWord(Base):
    __tablename__ = "daily_words"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    play_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    word: Mapped[str] = mapped_column(String(5), nullable=False)
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id"), nullable=True)

    season: Mapped["Season"] = relationship(back_populates="daily_words")


class DailyAttempt(Base):
    __tablename__ = "daily_attempts"
    __table_args__ = (UniqueConstraint("user_id", "play_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    play_date: Mapped[date] = mapped_column(Date, nullable=False)
    season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seasons.id"), nullable=True)
    guesses: Mapped[list] = mapped_column(JSON, default=list)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    won: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="attempts")
    season: Mapped["Season"] = relationship(back_populates="attempts")
