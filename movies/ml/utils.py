"""
Shared utility functions for the ML pipeline.
Consolidates duplicated helpers used across embedding, recommendation,
and explainability modules.
"""

from datetime import datetime
from typing import Dict


GENRE_MAP: Dict[int, str] = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
    10759: "Action & Adventure", 10765: "Sci-Fi & Fantasy",
}

GENRE_NAME_TO_ID: Dict[str, int] = {v: k for k, v in GENRE_MAP.items()}
GENRE_NAME_TO_ID["Sci-Fi"] = 878


def extract_year(date_str: str) -> int:
    if not date_str or len(date_str) < 4:
        return 0
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return 0


def recency_score(year: int) -> float:
    if year <= 0:
        return 0.0
    current_year = datetime.now().year
    age = max(0, current_year - year)
    if age <= 2:
        return 1.0
    elif age <= 5:
        return 0.8
    elif age <= 10:
        return 0.6
    elif age <= 20:
        return 0.4
    elif age <= 40:
        return 0.2
    return 0.1


def popularity_score(vote_average: float, popularity: float = 0) -> float:
    rating_score = min(1.0, max(0.0, (vote_average - 5.0) / 5.0)) if vote_average > 0 else 0.0
    pop_score = min(1.0, popularity / 200.0) if popularity > 0 else 0.0
    return 0.6 * rating_score + 0.4 * pop_score
