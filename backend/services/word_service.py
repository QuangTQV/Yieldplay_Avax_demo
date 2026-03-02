import random
from datetime import date, timedelta

# 5-letter word pool (expand in production)
WORD_POOL = [
    "crane", "slate", "audio", "stare", "raise", "arise", "irate",
    "snare", "share", "shore", "score", "store", "stove", "stone",
    "phone", "clone", "alone", "glare", "flare", "spare", "spire",
    "pride", "bride", "slide", "guide", "quite", "write", "white",
    "whole", "while", "chile", "smile", "style", "cycle", "table",
    "cable", "fable", "sable", "label", "maple", "apple", "ample",
    "blame", "flame", "frame", "shame", "trame", "claim", "plain",
    "train", "grain", "brain", "drain", "stain", "chain", "chair",
    "choir", "prior", "floor", "blood", "flood", "brood", "proof",
]

VALID_WORDS = set(WORD_POOL) | {
    # Additional valid guesses that aren't daily answers
    "adieu", "audio", "ouija", "queue", "fuzzy", "fizzy", "jazzy",
    "pizza", "waltz", "fjord", "glyph", "lynch", "myrrh", "pygmy",
    "tryst", "gypsy", "nymph", "crypt", "lymph", "crwth",
}


def get_daily_word_from_seed(play_date: date) -> str:
    """Deterministic word from date seed – same for all users on same day."""
    seed = play_date.year * 10000 + play_date.month * 100 + play_date.day
    random.seed(seed)
    return random.choice(WORD_POOL)


def is_valid_guess(word: str) -> bool:
    return len(word) == 5 and word.isalpha()


def generate_season_words(start_date: date, days: int = 30) -> dict[date, str]:
    """Pre-generate 30 daily words for a season."""
    words = {}
    for i in range(days):
        d = start_date + timedelta(days=i)
        words[d] = get_daily_word_from_seed(d)
    return words
