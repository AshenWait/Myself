from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import ScoreResult
from .tdx import normalize_symbol


def load_watchlist(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return {normalize_symbol(item["symbol"]): item for item in payload}
    if isinstance(payload, dict):
        return {normalize_symbol(item["symbol"]): item for item in payload.get("items", [])}
    raise ValueError(f"Unsupported watchlist format: {path}")


def save_watchlist(path: Path, items: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "items": sorted(items.values(), key=lambda item: item.get("score", 0), reverse=True),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def add_results(path: Path, results: Iterable[ScoreResult], min_score: float) -> int:
    items = load_watchlist(path)
    added = 0
    for result in results:
        if result.score < min_score:
            continue
        symbol = normalize_symbol(result.symbol)
        existed = symbol in items
        items[symbol] = {
            **asdict(result),
            "symbol": symbol,
            "added_at": items.get(symbol, {}).get("added_at") or datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        if not existed:
            added += 1
    save_watchlist(path, items)
    return added


def remove_symbol(path: Path, symbol: str) -> bool:
    items = load_watchlist(path)
    normalized = normalize_symbol(symbol)
    existed = normalized in items
    if existed:
        del items[normalized]
        save_watchlist(path, items)
    return existed


def export_csv(path: Path, output: Path) -> int:
    items = list(load_watchlist(path).values())
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["symbol", "name", "industry", "score", "bucket", "trade_date", "close", "added_at", "updated_at"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({field: item.get(field, "") for field in fields})
    return len(items)
