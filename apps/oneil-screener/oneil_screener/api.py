from __future__ import annotations

import argparse
import csv
import json
import threading
from dataclasses import asdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .cli import write_scores_csv, write_scores_json
from .models import ScoreResult
from .scoring import score_sqlite_universe, score_universe
from .smart_picks import (
    DeepSeekSmartPicker,
    SmartPicker,
    finalize_smart_picks,
    load_smart_picks,
    write_smart_picks,
)
from .tdx import is_screening_symbol, load_metadata_csv, normalize_symbol
from .tushare_data import TushareDataService
from .watchlist import add_results, load_watchlist, remove_symbol

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
RESULT_LIMIT = 50


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def result_from_dict(item: dict[str, Any]) -> ScoreResult:
    return ScoreResult(
        rank=_int(item.get("rank")),
        symbol=normalize_symbol(str(item.get("symbol", ""))),
        name=str(item.get("name", "")),
        industry=str(item.get("industry", "")),
        trade_date=str(item.get("trade_date", "")),
        close=_float(item.get("close")),
        score=_float(item.get("score")),
        bucket=str(item.get("bucket", "")),
        components={key: _float(value) for key, value in dict(item.get("components") or {}).items()},
        metrics={key: value for key, value in dict(item.get("metrics") or {}).items()},
        reasons=list(item.get("reasons") or []),
        flags=list(item.get("flags") or []),
    )


def result_from_csv_row(row: dict[str, str]) -> ScoreResult:
    return ScoreResult(
        rank=_int(row.get("rank")),
        symbol=normalize_symbol(row.get("symbol", "")),
        name=row.get("name", ""),
        industry=row.get("industry", ""),
        trade_date=row.get("trade_date", ""),
        close=_float(row.get("close")),
        score=_float(row.get("score")),
        bucket=row.get("bucket", ""),
        components={
            "trend": _float(row.get("trend_score")),
            "leader": _float(row.get("leader_score")),
            "volume": _float(row.get("volume_score")),
            "new_high": _float(row.get("new_high_score")),
            "market": _float(row.get("market_score")),
            "fundamental": _float(row.get("fundamental_score")),
        },
        metrics={"rs_rank": _float(row.get("rs_rank"))},
        reasons=[value for value in row.get("reasons", "").split(";") if value],
        flags=[value for value in row.get("flags", "").split(";") if value],
    )


class RuntimeStore:
    def __init__(
        self,
        app_root: Path,
        smart_picker: SmartPicker | None = None,
        tushare_service: TushareDataService | None = None,
    ):
        self.app_root = app_root.resolve()
        self.output_dir = self.app_root / "output"
        self.storage_dir = self.app_root / "storage"
        self.results_csv = self.output_dir / "oneil_scores.csv"
        self.results_json = self.output_dir / "oneil_scores.json"
        self.watchlist_json = self.storage_dir / "watchlist.json"
        self.smart_picks_json = self.storage_dir / "smart_picks.json"
        self.scan_meta_json = self.storage_dir / "scan_meta.json"
        self.smart_picker = smart_picker
        self.tushare = tushare_service or TushareDataService(self.app_root)
        self.lock = threading.Lock()

    def load_scan_meta(self) -> dict[str, Any]:
        if not self.scan_meta_json.exists():
            return {}
        payload = json.loads(self.scan_meta_json.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    def write_scan_meta(self, payload: dict[str, Any]) -> None:
        self.scan_meta_json.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.scan_meta_json.with_suffix(".tmp")
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.scan_meta_json)
        finally:
            if temporary.exists():
                temporary.unlink()

    def load_results(self) -> list[ScoreResult]:
        if self.results_json.exists():
            payload = json.loads(self.results_json.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise ValueError("Score JSON must contain a list")
            return [result_from_dict(item) for item in payload][:RESULT_LIMIT]

        if not self.results_csv.exists():
            return []

        with self.results_csv.open("r", encoding="utf-8-sig", newline="") as handle:
            return [result_from_csv_row(row) for row in csv.DictReader(handle)][:RESULT_LIMIT]

    def snapshot(self) -> dict[str, Any]:
        results = self.load_results()
        watchlist = sorted(
            (
                item
                for item in load_watchlist(self.watchlist_json).values()
                if is_screening_symbol(str(item.get("symbol", "")))
            ),
            key=lambda item: item.get("score", 0),
            reverse=True,
        )
        smart_picks = load_smart_picks(self.smart_picks_json)
        scan_meta = self.load_scan_meta()
        generated_file = self.results_json if self.results_json.exists() else self.results_csv
        generated_at = (
            datetime.fromtimestamp(generated_file.stat().st_mtime).isoformat(timespec="seconds")
            if generated_file.exists()
            else None
        )
        counts = {
            "total": len(results),
            "scanned_total": _int(scan_meta.get("scanned_total"), len(results)),
            "result_limit": RESULT_LIMIT,
            "a": _int(scan_meta.get("a"), sum(item.score >= 80 for item in results)),
            "b": _int(scan_meta.get("b"), sum(70 <= item.score < 80 for item in results)),
            "c": _int(scan_meta.get("c"), sum(60 <= item.score < 70 for item in results)),
            "rejected": _int(scan_meta.get("rejected"), sum(item.score < 60 for item in results)),
            "watchlist": len(watchlist),
            "smart": len(smart_picks["picks"]),
        }
        return {
            "results": [asdict(item) for item in results],
            "watchlist": watchlist,
            "smart_picks": smart_picks,
            "summary": counts,
            "generated_at": generated_at,
            "data_sources": {
                "active": str(scan_meta.get("data_source") or "tdx"),
                "tushare": self.tushare.status(),
            },
        }

    def scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        data_source = str(payload.get("data_source") or "tdx").strip().lower()
        if data_source not in {"tdx", "tushare"}:
            raise ValueError("data_source 必须是 tdx 或 tushare")

        with self.lock:
            if data_source == "tdx":
                raw_root = str(payload.get("tdx_root") or "").strip()
                if not raw_root:
                    raise ValueError("tdx_root is required")
                data_path = Path(raw_root).expanduser()
                if not data_path.exists():
                    raise FileNotFoundError(f"Tongdaxin path does not exist: {data_path}")
                metadata_value = str(payload.get("metadata_csv") or "").strip()
                metadata_path = Path(metadata_value).expanduser() if metadata_value else None
                if metadata_path is not None and not metadata_path.exists():
                    raise FileNotFoundError(f"Metadata CSV does not exist: {metadata_path}")
                all_results = score_universe(
                    tdx_root=data_path,
                    benchmark_symbol=str(payload.get("benchmark") or "sh000001"),
                    metadata=load_metadata_csv(metadata_path),
                )
            else:
                status = self.tushare.status()
                if not status["ready"]:
                    message = status.get("last_error") or "服务器行情正在初始化，请稍后刷新"
                    raise ValueError(message)
                data_path = self.tushare.database.path
                all_results = score_sqlite_universe(data_path)

            results = all_results[:RESULT_LIMIT]
            write_scores_csv(self.results_csv, results)
            write_scores_json(self.results_json, results)
            self.write_scan_meta(
                {
                    "data_source": data_source,
                    "data_path": str(data_path.resolve()),
                    "scanned_total": len(all_results),
                    "result_limit": RESULT_LIMIT,
                    "a": sum(item.score >= 80 for item in all_results),
                    "b": sum(70 <= item.score < 80 for item in all_results),
                    "c": sum(60 <= item.score < 70 for item in all_results),
                    "rejected": sum(item.score < 60 for item in all_results),
                    "trade_date": results[0].trade_date if results else None,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            return self.snapshot()

    def select_smart_picks(self, payload: dict[str, Any]) -> dict[str, Any]:
        requested_source = str(payload.get("data_source") or "tdx").strip().lower()
        results = self.load_results()
        scan_meta = self.load_scan_meta()
        source_changed = scan_meta.get("data_source") != requested_source
        if not results or source_changed:
            self.scan(payload)
            results = self.load_results()
            scan_meta = self.load_scan_meta()
        if len(results) < 3:
            raise ValueError("扫描结果少于 3 只，无法生成智选组合")

        raw_path = str(scan_meta.get("data_path") or "").strip()
        candidate_path = Path(raw_path) if raw_path else None
        data_path = candidate_path if candidate_path is not None and candidate_path.exists() else None
        candidates = results[:10]
        picker = self.smart_picker or DeepSeekSmartPicker(self.app_root)
        raw_picks = picker.select(candidates, data_path)
        smart_picks = finalize_smart_picks(raw_picks, candidates, picker.model_name)
        with self.lock:
            write_smart_picks(self.smart_picks_json, smart_picks)
        return self.snapshot()

    def start_tushare_sync(self) -> dict[str, Any]:
        self.tushare.start_sync()
        return self.snapshot()

    def start_scheduler(self) -> None:
        self.tushare.start_scheduler()

    def close(self) -> None:
        self.tushare.stop()

    def add_to_watchlist(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        with self.lock:
            result = next((item for item in self.load_results() if item.symbol == normalized), None)
            if result is None:
                raise ValueError(f"Symbol is not present in the latest screen: {normalized}")
            add_results(self.watchlist_json, [result], min_score=0)
            return self.snapshot()

    def remove_from_watchlist(self, symbol: str) -> dict[str, Any]:
        with self.lock:
            remove_symbol(self.watchlist_json, symbol)
            return self.snapshot()


class ScreenerHttpServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], store: RuntimeStore):
        super().__init__(address, ScreenerRequestHandler)
        self.store = store


class ScreenerRequestHandler(BaseHTTPRequestHandler):
    server: ScreenerHttpServer

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = _int(self.headers.get("Content-Length"))
        if length == 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        return payload

    def _handle_error(self, error: Exception) -> None:
        status = 400 if isinstance(error, (ValueError, FileNotFoundError, json.JSONDecodeError)) else 500
        self._send_json(status, {"error": str(error) or error.__class__.__name__})

    def do_OPTIONS(self) -> None:
        self._send_json(204, {})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                snapshot = self.server.store.snapshot()
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "results": snapshot["summary"]["total"],
                        "scanned": snapshot["summary"]["scanned_total"],
                        "watchlist": snapshot["summary"]["watchlist"],
                        "smart": snapshot["summary"]["smart"],
                    },
                )
                return
            if path == "/api/screener":
                self._send_json(200, self.server.store.snapshot())
                return
            self._send_json(404, {"error": "Not found"})
        except Exception as error:
            self._handle_error(error)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/scan":
                self._send_json(200, self.server.store.scan(payload))
                return
            if path == "/api/watchlist":
                self._send_json(200, self.server.store.add_to_watchlist(str(payload.get("symbol") or "")))
                return
            if path == "/api/smart-picks":
                self._send_json(200, self.server.store.select_smart_picks(payload))
                return
            if path == "/api/tushare/sync":
                self._send_json(202, self.server.store.start_tushare_sync())
                return
            self._send_json(404, {"error": "Not found"})
        except Exception as error:
            self._handle_error(error)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        prefix = "/api/watchlist/"
        try:
            if path.startswith(prefix):
                symbol = unquote(path[len(prefix) :])
                self._send_json(200, self.server.store.remove_from_watchlist(symbol))
                return
            self._send_json(404, {"error": "Not found"})
        except Exception as error:
            self._handle_error(error)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[oneil-api] {self.address_string()} {format % args}")


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    app_root: Path | None = None,
    smart_picker: SmartPicker | None = None,
    tushare_service: TushareDataService | None = None,
) -> ScreenerHttpServer:
    root = app_root or Path(__file__).resolve().parents[1]
    return ScreenerHttpServer((host, port), RuntimeStore(root, smart_picker, tushare_service))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local O'Neil screener API.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    args = parser.parse_args(argv)

    server = create_server(args.host, args.port)
    server.store.start_scheduler()
    print(f"O'Neil screener API listening on http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.store.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
