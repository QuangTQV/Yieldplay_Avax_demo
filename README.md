# 🟩 WordlePlay – YieldPlay Season Mode

A full-stack Wordle game with 30-day seasons powered by YieldPlay SDK (mock).
Players stake USDC → earn yield → top players share the reward pool.

---

## Architecture

```
wordle-season/
├── backend/             # FastAPI + SQLAlchemy (Python)
│   ├── main.py
│   ├── models.py        # ORM models
│   ├── schemas.py       # Pydantic schemas
│   ├── config.py
│   ├── database.py
│   ├── routers/
│   │   ├── users.py
│   │   ├── seasons.py   # join-season, end-season → YieldPlay
│   │   ├── game.py      # start, guess
│   │   └── leaderboard.py
│   └── services/
│       ├── scoring.py       # score formula
│       ├── word_service.py  # deterministic daily words
│       └── yieldplay_mock.py  # mock SDK
├── frontend/            # React + Vite
│   └── src/
│       ├── pages/
│       │   ├── LoginPage.jsx
│       │   ├── JoinSeasonPage.jsx   # stake USDC UI
│       │   ├── GamePage.jsx         # Wordle board
│       │   ├── LeaderboardPage.jsx
│       │   └── ProgressPage.jsx     # 30-day calendar
│       └── components/
│           ├── WordleGrid.jsx
│           └── Keyboard.jsx
└── db/
    └── schema.sql
```

---

## Scoring Formula

```
Score_day = (7 - attempts) × 100 - floor(time_seconds / 10)

Rules:
- Lost:            0 points
- Max time:        600s (capped)
- Not played:      0 points

Season_score = Σ(daily scores over 30 days)
```

## YieldPlay Flow

```
1. User stakes 10 USDC
   ├── 0.20 USDC → Participation fee → Reward Pool (Base)
   └── 9.80 USDC → Principal → Lending/Yield strategy

2. Over 30 days: principal earns ~4.5% APY
   Reward Pool += yield generated

3. Season ends:
   POST /seasons/{id}/end
   → Submits leaderboard to YieldPlay
   → YieldPlay distributes: 🥇50% 🥈30% 🥉20%
```

---

## Quick Start

### Docker (recommended)
```bash
docker-compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/docs
```

### Manual

**Backend**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL
uvicorn main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

**Database**
```bash
createdb wordle_season
psql wordle_season < db/schema.sql
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /users | Register user |
| GET | /seasons/active | Get active season |
| POST | /seasons/join | Join season (stake) |
| POST | /seasons/{id}/end | Admin: end season → YieldPlay |
| POST | /game/start | Start today's game |
| POST | /game/guess | Submit a guess |
| GET | /game/state/{user_id} | Get current game state |
| GET | /leaderboard/{season_id} | Season leaderboard |
| GET | /leaderboard/progress/{season_id}/{user_id} | User's season progress |

Interactive docs: `http://localhost:8000/docs`
