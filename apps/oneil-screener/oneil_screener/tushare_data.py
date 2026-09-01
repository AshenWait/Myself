from __future__ import annotations

import json
import os
import sqlite3
import threading
import time as time_module
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .models import PriceBar, StockMetadata, StockSeries
from .tdx import is_screening_symbol, normalize_symbol

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
DEFAULT_SYNC_TIME = "18:10"
DEFAULT_HISTORY_DAYS = 270


class TushareClient(Protocol):
    def query(self, api_name: str, params: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class TushareConfig:
    token: str
    api_url: str
    sync_time: str
    history_days: int
    auto_sync: bool


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def load_tushare_config(app_root: Path) -> TushareConfig:
    values: dict[str, str] = {}
    values.update(_read_env_file(app_root.parent / "knowledge-agent" / ".env"))
    values.update(_read_env_file(app_root / ".env"))

    def setting(name: str, fallback: str = "") -> str:
        return os.environ.get(name) or values.get(name) or fallback

    token = setting("TUSHARE_TOKEN")
    history_days = int(setting("TUSHARE_HISTORY_DAYS", str(DEFAULT_HISTORY_DAYS)))
    if history_days < 260:
        raise ValueError("TUSHARE_HISTORY_DAYS 不能少于 260")
    auto_sync = setting("TUSHARE_AUTO_SYNC", "true").lower() not in {"0", "false", "no", "off"}
    sync_time = setting("TUSHARE_SYNC_TIME", DEFAULT_SYNC_TIME)
    datetime.strptime(sync_time, "%H:%M")
    return TushareConfig(
        token=token,
        api_url=setting("TUSHARE_API_URL", "https://api.tushare.pro"),
        sync_time=sync_time,
        history_days=history_days,
        auto_sync=auto_sync,
    )


class TushareHttpClient:
    def __init__(self, token: str, api_url: str):
        if not token or token.lower().startswith(("replace", "your")) or "你的" in token:
            raise ValueError("未配置有效的 TUSHARE_TOKEN")
        self.token = token
        self.api_url = api_url

    def query(self, api_name: str, params: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]:
        payload = {
            "api_name": api_name,
            "token": self.token,
            "params": params,
            "fields": ",".join(fields),
        }
        for attempt in range(3):
            request = Request(
                self.api_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=45) as response:
                    result = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")[:300]
                raise RuntimeError(f"Tushare 请求失败 (HTTP {error.code}): {detail}") from error
            except URLError as error:
                raise RuntimeError(f"无法连接 Tushare: {error.reason}") from error

            if result.get("code") == 0:
                data = result.get("data") or {}
                response_fields = data.get("fields") or []
                return [dict(zip(response_fields, item)) for item in data.get("items") or []]
            message = str(result.get("msg") or result.get("code"))
            if "频率超限" in message and "次/小时" not in message and attempt < 2:
                time_module.sleep(65)
                continue
            raise RuntimeError(f"Tushare 接口 {api_name} 返回错误: {message}")
        raise RuntimeError(f"Tushare 接口 {api_name} 重试失败")


def _symbol_from_tushare(value: str) -> str:
    code, _, exchange = value.upper().partition(".")
    if len(code) != 6:
        raise ValueError(f"无效的 Tushare 股票代码: {value}")
    market = "sh" if exchange == "SH" else "sz"
    return normalize_symbol(f"{market}{code}")


def _iso_date(value: str) -> str:
    parsed = datetime.strptime(value, "%Y%m%d").date()
    return parsed.isoformat()


class TushareDatabase:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS daily (
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                amount REAL NOT NULL,
                volume INTEGER NOT NULL,
                PRIMARY KEY (symbol, trade_date)
            );
            CREATE INDEX IF NOT EXISTS idx_daily_trade_date ON daily(trade_date);
            CREATE TABLE IF NOT EXISTS metadata (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                industry TEXT NOT NULL DEFAULT ''
            );
            """
        )
        return connection

    def save_stock_rows(self, rows: list[dict[str, Any]]) -> int:
        records: list[tuple[Any, ...]] = []
        for row in rows:
            symbol = _symbol_from_tushare(str(row["ts_code"]))
            if not is_screening_symbol(symbol):
                continue
            records.append(
                (
                    symbol,
                    _iso_date(str(row["trade_date"])),
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row.get("amount") or 0) * 1000,
                    int(round(float(row.get("vol") or 0) * 100)),
                )
            )
        if not records:
            return 0
        with closing(self.connect()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT OR REPLACE INTO daily
                    (symbol, trade_date, open, high, low, close, amount, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO metadata (symbol) VALUES (?)",
                    [(record[0],) for record in records],
                )
        return len(records)

    def save_index_rows(self, rows: list[dict[str, Any]]) -> int:
        records = [
            (
                "sh000001",
                _iso_date(str(row["trade_date"])),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row.get("amount") or 0) * 1000,
                int(round(float(row.get("vol") or 0) * 100)),
            )
            for row in rows
        ]
        if not records:
            return 0
        with closing(self.connect()) as connection:
            with connection:
                connection.executemany(
                    """
                    INSERT OR REPLACE INTO daily
                    (symbol, trade_date, open, high, low, close, amount, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
        return len(records)

    def save_metadata(self, rows: list[dict[str, Any]]) -> int:
        records: list[tuple[str, str, str]] = []
        for row in rows:
            symbol = _symbol_from_tushare(str(row["ts_code"]))
            if is_screening_symbol(symbol):
                records.append((symbol, str(row.get("name") or ""), str(row.get("industry") or "")))
        with closing(self.connect()) as connection:
            with connection:
                connection.executemany(
                    "INSERT OR REPLACE INTO metadata (symbol, name, industry) VALUES (?, ?, ?)",
                    records,
                )
        return len(records)

    def latest_date(self, symbol: str | None = None) -> str | None:
        if not self.path.exists():
            return None
        with closing(self.connect()) as connection:
            if symbol:
                row = connection.execute("SELECT MAX(trade_date) FROM daily WHERE symbol = ?", (symbol,)).fetchone()
            else:
                row = connection.execute("SELECT MAX(trade_date) FROM daily WHERE symbol != 'sh000001'").fetchone()
        return str(row[0]) if row and row[0] else None

    def earliest_date(self) -> str | None:
        if not self.path.exists():
            return None
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT MIN(trade_date) FROM daily WHERE symbol != 'sh000001'"
            ).fetchone()
        return str(row[0]) if row and row[0] else None

    def build_synthetic_index(self) -> int:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                """
                SELECT trade_date,
                       AVG((close - open) / open) AS average_return,
                       SUM(amount) AS total_amount,
                       SUM(volume) AS total_volume
                FROM daily
                WHERE symbol != 'sh000001' AND open > 0
                GROUP BY trade_date
                ORDER BY trade_date
                """
            ).fetchall()
            level = 1000.0
            records: list[tuple[Any, ...]] = []
            for trade_date, average_return, amount, volume in rows:
                previous = level
                level = previous * (1 + float(average_return or 0))
                records.append(
                    (
                        "sh000001",
                        str(trade_date),
                        previous,
                        max(previous, level),
                        min(previous, level),
                        level,
                        float(amount or 0),
                        int(volume or 0),
                    )
                )
            with connection:
                connection.execute("DELETE FROM daily WHERE symbol = 'sh000001'")
                connection.executemany(
                    """
                    INSERT INTO daily
                    (symbol, trade_date, open, high, low, close, amount, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    records,
                )
        return len(records)

    def summary(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "latest_trade_date": None,
                "stock_count": 0,
                "named_stock_count": 0,
                "benchmark_days": 0,
                "ready": False,
            }
        with closing(self.connect()) as connection:
            latest = connection.execute(
                "SELECT MAX(trade_date) FROM daily WHERE symbol != 'sh000001'"
            ).fetchone()[0]
            stock_count = connection.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
            named_stock_count = connection.execute(
                "SELECT COUNT(*) FROM metadata WHERE name IS NOT NULL AND name != ''"
            ).fetchone()[0]
            benchmark_days = connection.execute(
                "SELECT COUNT(*) FROM daily WHERE symbol = 'sh000001'"
            ).fetchone()[0]
        return {
            "latest_trade_date": latest,
            "stock_count": stock_count,
            "named_stock_count": named_stock_count,
            "benchmark_days": benchmark_days,
            "ready": bool(latest and stock_count and benchmark_days >= 220),
        }


def _price_bar(row: sqlite3.Row) -> PriceBar:
    return PriceBar(
        trade_date=date.fromisoformat(str(row["trade_date"])),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        amount=float(row["amount"]),
        volume=int(row["volume"]),
    )


def load_sqlite_series(path: Path, symbol: str, max_records: int = 260) -> StockSeries:
    normalized = normalize_symbol(symbol)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        metadata = connection.execute(
            "SELECT name, industry FROM metadata WHERE symbol = ?", (normalized,)
        ).fetchone()
        rows = connection.execute(
            """
            SELECT trade_date, open, high, low, close, amount, volume
            FROM daily WHERE symbol = ? ORDER BY trade_date DESC LIMIT ?
            """,
            (normalized, max_records),
        ).fetchall()
    finally:
        connection.close()
    bars = [_price_bar(row) for row in reversed(rows)]
    return StockSeries(
        symbol=normalized,
        name=str(metadata["name"]) if metadata else "",
        industry=str(metadata["industry"]) if metadata else "",
        bars=bars,
    )


def load_sqlite_universe(
    path: Path, min_history: int = 220
) -> tuple[list[PriceBar], list[StockSeries], dict[str, StockMetadata]]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        metadata_rows = connection.execute(
            "SELECT symbol, name, industry FROM metadata ORDER BY symbol"
        ).fetchall()
    finally:
        connection.close()

    metadata = {
        str(row["symbol"]): StockMetadata(
            symbol=str(row["symbol"]), name=str(row["name"]), industry=str(row["industry"])
        )
        for row in metadata_rows
        if is_screening_symbol(str(row["symbol"]))
    }
    benchmark = load_sqlite_series(path, "sh000001").bars
    series = [load_sqlite_series(path, symbol) for symbol in metadata]
    return benchmark, [item for item in series if len(item.bars) >= min_history], metadata


class TushareDataService:
    def __init__(self, app_root: Path, client: TushareClient | None = None):
        self.app_root = app_root.resolve()
        self.database = TushareDatabase(self.app_root / "data" / "tushare" / "market.sqlite3")
        self.state_path = self.app_root / "storage" / "tushare_sync.json"
        self.client = client
        self.request_interval = 1.3 if client is None else 0.0
        self._sync_lock = threading.Lock()
        self._sync_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._scheduler_thread: threading.Thread | None = None

    def _config(self) -> TushareConfig:
        return load_tushare_config(self.app_root)

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, **updates: Any) -> None:
        payload = {**self._load_state(), **updates}
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.state_path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def status(self) -> dict[str, Any]:
        try:
            config = self._config()
            configured = bool(config.token)
            schedule = config.sync_time
            automatic = config.auto_sync
        except (ValueError, TypeError):
            configured = False
            schedule = DEFAULT_SYNC_TIME
            automatic = False
        return {
            "configured": configured,
            "automatic": automatic,
            "schedule": schedule,
            "syncing": bool(self._sync_thread and self._sync_thread.is_alive()),
            **self.database.summary(),
            **self._load_state(),
        }

    def sync(self, today: date | None = None) -> dict[str, Any]:
        if not self._sync_lock.acquire(blocking=False):
            return self.status()
        try:
            config = self._config()
            client = self.client or TushareHttpClient(config.token, config.api_url)
            current_date = today or datetime.now(SHANGHAI_TZ).date()
            latest = self.database.latest_date()
            stock_start = (
                date.fromisoformat(latest) + timedelta(days=1)
                if latest
                else current_date - timedelta(days=round(config.history_days * 1.65))
            )
            self._write_state(
                status="syncing",
                started_at=datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds"),
                last_error="",
                progress=0,
                progress_total=0,
            )

            candidate_dates: list[str] = []
            cursor = stock_start
            while cursor <= current_date:
                if cursor.weekday() < 5:
                    candidate_dates.append(cursor.strftime("%Y%m%d"))
                cursor += timedelta(days=1)

            if self.database.summary()["named_stock_count"] == 0:
                try:
                    metadata_rows = client.query(
                        "stock_basic",
                        {"exchange": "", "list_status": "L"},
                        ["ts_code", "name", "industry"],
                    )
                    self.database.save_metadata(metadata_rows)
                    self._write_state(metadata_warning="")
                except RuntimeError as error:
                    self._write_state(metadata_warning=str(error))
            self._write_state(progress=0, progress_total=len(candidate_dates))

            for index, trade_date in enumerate(candidate_dates, start=1):
                if index > 1 and self.request_interval:
                    time_module.sleep(self.request_interval)
                rows = client.query(
                    "daily",
                    {"trade_date": trade_date},
                    ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"],
                )
                self.database.save_stock_rows(rows)
                if index == len(candidate_dates) or index % 5 == 0:
                    self._write_state(progress=index, progress_total=len(candidate_dates), current_trade_date=trade_date)

            earliest_stock = self.database.earliest_date()
            benchmark_source = "synthetic"
            if earliest_stock:
                try:
                    index_rows = client.query(
                        "index_daily",
                        {
                            "ts_code": "000001.SH",
                            "start_date": date.fromisoformat(earliest_stock).strftime("%Y%m%d"),
                            "end_date": current_date.strftime("%Y%m%d"),
                        },
                        ["trade_date", "open", "high", "low", "close", "vol", "amount"],
                    )
                    self.database.save_index_rows(index_rows)
                    benchmark_source = "tushare"
                    self._write_state(benchmark_warning="")
                except RuntimeError as error:
                    self._write_state(benchmark_warning=str(error))
            if benchmark_source == "synthetic":
                self.database.build_synthetic_index()

            self._write_state(
                status="idle",
                completed_at=datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds"),
                checked_through=current_date.isoformat(),
                last_error="",
                benchmark_source=benchmark_source,
                progress=len(candidate_dates),
                progress_total=len(candidate_dates),
            )
            return self.status()
        except Exception as error:
            self._write_state(
                status="error",
                completed_at=datetime.now(SHANGHAI_TZ).isoformat(timespec="seconds"),
                last_error=str(error) or error.__class__.__name__,
            )
            raise
        finally:
            self._sync_lock.release()

    def start_sync(self) -> dict[str, Any]:
        if self._sync_thread and self._sync_thread.is_alive():
            return self.status()

        def run() -> None:
            try:
                self.sync()
            except Exception as error:
                print(f"[oneil-api] Tushare sync failed: {error}")

        self._sync_thread = threading.Thread(target=run, name="tushare-sync", daemon=True)
        self._sync_thread.start()
        return self.status()

    def start_scheduler(self) -> None:
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return

        def run() -> None:
            while not self._stop.is_set():
                try:
                    config = self._config()
                    status = self.status()
                    now = datetime.now(SHANGHAI_TZ)
                    scheduled = time.fromisoformat(config.sync_time)
                    completed_at = status.get("completed_at")
                    retry_allowed = True
                    if status.get("status") == "error" and completed_at:
                        last_attempt = datetime.fromisoformat(str(completed_at))
                        retry_allowed = now - last_attempt >= timedelta(minutes=5)
                    should_initialize = config.auto_sync and config.token and not status["ready"] and retry_allowed
                    should_update = (
                        config.auto_sync
                        and config.token
                        and now.time() >= scheduled
                        and status.get("checked_through") != now.date().isoformat()
                        and retry_allowed
                    )
                    if (should_initialize or should_update) and not status["syncing"]:
                        self.start_sync()
                except Exception as error:
                    print(f"[oneil-api] Tushare scheduler check failed: {error}")
                self._stop.wait(60)

        self._scheduler_thread = threading.Thread(target=run, name="tushare-scheduler", daemon=True)
        self._scheduler_thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2)
