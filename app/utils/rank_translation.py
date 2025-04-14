import json
import os

TRANSLATIONS_PATH = os.path.join(os.path.dirname(__file__), "rank_translations.json")


def load_rank_translations() -> dict:
    with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Кешируем при импорте
RANK_TRANSLATIONS = load_rank_translations()


def translate_rank(rank: str) -> str:
    return RANK_TRANSLATIONS.get(rank.lower(), rank)
