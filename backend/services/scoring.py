import math

from services.types import LetterEval, LetterStatus

MAX_TIME_SECONDS: int = 600
MAX_ATTEMPTS: int = 6


def calculate_score(attempts: int, time_seconds: int, won: bool) -> int:
    """
    Score_day = (7 - attempts) × 100 - floor(time_seconds / 10)
    - Thua:          0 điểm
    - Time tối đa:   600s (capped)
    """
    if not won:
        return 0

    capped_time = min(time_seconds, MAX_TIME_SECONDS)
    score = (7 - attempts) * 100 - math.floor(capped_time / 10)
    return max(0, score)


def evaluate_guess(guess: str, answer: str) -> list[LetterEval]:
    """
    So sánh guess với answer, trả về danh sách LetterEval.

    Status:
      - correct  : đúng chữ, đúng vị trí
      - present  : đúng chữ, sai vị trí
      - absent   : chữ không có trong từ
    """
    statuses: list[LetterStatus] = ["absent"] * len(guess)
    answer_pool: list[str | None] = list(answer)

    # Pass 1 – đánh dấu correct
    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            statuses[i] = "correct"
            answer_pool[i] = None

    # Pass 2 – đánh dấu present
    for i, g in enumerate(guess):
        if statuses[i] == "correct":
            continue
        if g in answer_pool:
            statuses[i] = "present"
            answer_pool[answer_pool.index(g)] = None

    return [
        LetterEval(letter=letter, status=status)
        for letter, status in zip(guess, statuses)
    ]
