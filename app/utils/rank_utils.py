# utils/rank_utils.py

RANK_ORDER = {
    "unrated": 0,
    "newbie": 1,
    "pupil": 2,
    "specialist": 3,
    "expert": 4,
    "candidate master": 5,
    "master": 6,
    "international master": 7,
    "grandmaster": 8,
    "international grandmaster": 9,
    "legendary grandmaster": 10
}


def compare_ranks(rank1: str, rank2: str) -> int:
    """
    Возвращает:
        > 0 если rank1 выше
        < 0 если rank2 выше
        = 0 если равны
    """
    val1 = RANK_ORDER.get(rank1.lower(), 0)
    val2 = RANK_ORDER.get(rank2.lower(), 0)
    return val1 > val2 and val1 >= 3
