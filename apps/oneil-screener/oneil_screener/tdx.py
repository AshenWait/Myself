from __future__ import annotations

import csv
import struct
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import PriceBar, StockMetadata, StockSeries

DAY_RECORD = struct.Struct("<IIIIIfII")
TNF_HEADER_SIZE = 50
TNF_RECORD_SIZE = 360
TNF_NAME_OFFSET = 31
TNF_NAME_SIZE = 32


def normalize_symbol(value: str) -> str:
    raw = value.strip().lower().replace(".", "").replace("_", "")
    if raw.startswith(("sh", "sz")) and len(raw) >= 8:
        return raw[:8]
    code = "".join(ch for ch in raw if ch.isdigit())
    if len(code) != 6:
        raise ValueError(f"Cannot normalize stock symbol: {value!r}")
    market = "sh" if code.startswith("6") else "sz"
    return f"{market}{code}"


def is_a_share_symbol(symbol: str) -> bool:
    symbol = normalize_symbol(symbol)
    market, code = symbol[:2], symbol[2:]
    if market == "sh":
        return code.startswith("6")
    if market == "sz":
        return code.startswith(("0", "3")) and not code.startswith("399")
    return False


def is_screening_symbol(symbol: str) -> bool:
    code = normalize_symbol(symbol)[2:]
    return code.startswith(("60", "00"))


def read_day_file(path: Path, symbol: str | None = None, name: str = "", max_records: int | None = None) -> StockSeries:
    data = path.read_bytes()
    count = len(data) // DAY_RECORD.size
    if max_records is not None:
        count = min(count, max_records)

    bars: list[PriceBar] = []
    for offset in range(0, count * DAY_RECORD.size, DAY_RECORD.size):
        raw_date, raw_open, raw_high, raw_low, raw_close, amount, volume, _ = DAY_RECORD.unpack_from(data, offset)
        yyyy = raw_date // 10000
        mm = raw_date // 100 % 100
        dd = raw_date % 100
        bars.append(
            PriceBar(
                trade_date=date(yyyy, mm, dd),
                open=raw_open / 100.0,
                high=raw_high / 100.0,
                low=raw_low / 100.0,
                close=raw_close / 100.0,
                amount=float(amount),
                volume=int(volume),
            )
        )

    inferred_symbol = symbol or path.stem.lower()
    return StockSeries(symbol=normalize_symbol(inferred_symbol), name=name, bars=bars)


def find_lday_dirs(tdx_root: Path, markets: Iterable[str] = ("sh", "sz")) -> dict[str, Path]:
    root = tdx_root.expanduser().resolve()
    result: dict[str, Path] = {}
    for market in markets:
        candidates = [
            root / "vipdoc" / market / "lday",
            root / market / "lday",
        ]
        if root.name.lower() == "lday":
            candidates.append(root)
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                result[market] = candidate
                break
    return result


def load_tdx_stock_names(tdx_root: Path, markets: Iterable[str] = ("sh", "sz")) -> dict[str, str]:
    root = tdx_root.expanduser().resolve()
    cache_dirs = [root / "T0002" / "hq_cache", root / "hq_cache"]
    result: dict[str, str] = {}

    for market in markets:
        name_file = next(
            (
                cache_dir / filename
                for cache_dir in cache_dirs
                for filename in (f"{market}s.tnf", f"{market}m.tnf")
                if (cache_dir / filename).exists()
            ),
            None,
        )
        if name_file is None:
            continue

        data = name_file.read_bytes()
        for offset in range(TNF_HEADER_SIZE, len(data) - TNF_RECORD_SIZE + 1, TNF_RECORD_SIZE):
            record = data[offset : offset + TNF_RECORD_SIZE]
            code = record[:6].decode("ascii", errors="ignore")
            if len(code) != 6 or not code.isdigit():
                continue
            symbol = f"{market}{code}"
            if not is_a_share_symbol(symbol):
                continue
            raw_name = record[TNF_NAME_OFFSET : TNF_NAME_OFFSET + TNF_NAME_SIZE].split(b"\x00", 1)[0]
            name = raw_name.decode("gbk", errors="ignore").strip()
            if name:
                result[symbol] = name
    return result


def iter_stock_day_files(tdx_root: Path, markets: Iterable[str] = ("sh", "sz")) -> Iterable[tuple[str, Path]]:
    for market, lday_dir in find_lday_dirs(tdx_root, markets).items():
        for path in sorted(lday_dir.glob(f"{market}*.day")):
            symbol = path.stem.lower()
            if is_a_share_symbol(symbol):
                yield symbol, path


def find_day_file(tdx_root: Path, symbol: str) -> Path:
    symbol = normalize_symbol(symbol)
    market = symbol[:2]
    lday_dirs = find_lday_dirs(tdx_root, (market,))
    if market not in lday_dirs:
        raise FileNotFoundError(f"Cannot find Tongdaxin lday directory for {market} under {tdx_root}")
    path = lday_dirs[market] / f"{symbol}.day"
    if not path.exists():
        raise FileNotFoundError(f"Cannot find Tongdaxin day file: {path}")
    return path


def load_metadata_csv(path: Path | None) -> dict[str, StockMetadata]:
    if path is None:
        return {}

    metrics = {
        "eps_yoy",
        "revenue_yoy",
        "eps_3y_cagr",
        "roe",
        "float_market_cap",
        "institutional_ownership",
    }
    result: dict[str, StockMetadata] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "symbol" not in reader.fieldnames:
            raise ValueError("metadata CSV must contain a 'symbol' column")
        for row in reader:
            symbol = normalize_symbol(row["symbol"])
            parsed: dict[str, float] = {}
            for key in metrics:
                value = (row.get(key) or "").strip()
                if value:
                    parsed[key] = float(value)
            result[symbol] = StockMetadata(
                symbol=symbol,
                name=(row.get("name") or "").strip(),
                industry=(row.get("industry") or "").strip(),
                metrics=parsed,
            )
    return result
