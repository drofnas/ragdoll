from __future__ import annotations

def percentage_used(current: int, limit: int | None) -> float | None:
    if limit in (None, 0):
        return None
    return round((current / limit) * 100, 2)
