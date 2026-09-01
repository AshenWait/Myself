from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from oneil_screener.api import create_server
from oneil_screener.tdx import DAY_RECORD
from oneil_screener.tushare_data import TushareDataService


def write_day_file(path: Path, prices: list[float], start: date = date(2025, 1, 1)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for index, close in enumerate(prices):
            trade_date = start + timedelta(days=index)
            raw_date = trade_date.year * 10000 + trade_date.month * 100 + trade_date.day
            cents = int(round(close * 100))
            volume = 10_000 + index * 100
            handle.write(DAY_RECORD.pack(raw_date, cents, cents + 10, cents - 10, cents, float(cents * volume), volume, 0))


def trend(start: float, step: float, days: int = 260) -> list[float]:
    return [round(start + step * index, 2) for index in range(days)]


def request_json(base_url: str, path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


class FakeSmartPicker:
    model_name = "fake-smart-model"

    def __init__(self) -> None:
        self.candidate_symbols: list[str] = []

    def select(self, candidates, tdx_root):
        self.candidate_symbols = [item.symbol for item in candidates]
        picks = []
        for item in candidates[:3]:
            picks.append(
                {
                    "symbol": item.symbol,
                    "confidence": 80,
                    "holding_period": "3-10个交易日",
                    "entry_low": round(item.close * 0.98, 2),
                    "entry_high": round(item.close, 2),
                    "stop_loss": round(item.close * 0.93, 2),
                    "take_profit_1": round(item.close * 1.08, 2),
                    "take_profit_2": round(item.close * 1.15, 2),
                    "thesis": "趋势与量能在候选中占优",
                    "entry_logic": "回踩买入区间且未跌破短期支撑",
                    "stop_logic": "收盘跌破止损价后退出观察",
                    "take_profit_logic": "达到目标价后分两次止盈",
                    "risks": ["放量跌破短期均线"],
                }
            )
        return {"market_view": "测试市场判断", "selection_logic": "测试选择逻辑", "picks": picks}


class FakeTushareClient:
    def __init__(self, trade_dates: list[date], stock_count: int = 55) -> None:
        self.trade_dates = trade_dates
        self.symbols = [f"{600001 + index:06d}.SH" for index in range(stock_count)]

    def query(self, api_name, params, fields):
        if api_name == "trade_cal":
            return [{"cal_date": item.strftime("%Y%m%d"), "is_open": "1"} for item in self.trade_dates]
        if api_name == "stock_basic":
            return [
                {"ts_code": symbol, "name": f"测试股票{index + 1}", "industry": "测试行业"}
                for index, symbol in enumerate(self.symbols)
            ]
        if api_name == "daily":
            trade_date = datetime.strptime(params["trade_date"], "%Y%m%d").date()
            if trade_date not in self.trade_dates:
                return []
            day_index = self.trade_dates.index(trade_date)
            return [
                {
                    "ts_code": symbol,
                    "trade_date": params["trade_date"],
                    "open": 10 + stock_index * 0.1 + day_index * 0.03,
                    "high": 10.2 + stock_index * 0.1 + day_index * 0.03,
                    "low": 9.8 + stock_index * 0.1 + day_index * 0.03,
                    "close": 10.1 + stock_index * 0.1 + day_index * 0.03,
                    "vol": 10000 + day_index * 10,
                    "amount": 100000 + day_index * 100,
                }
                for stock_index, symbol in enumerate(self.symbols)
            ]
        if api_name == "index_daily":
            return [
                {
                    "trade_date": item.strftime("%Y%m%d"),
                    "open": 3000 + index,
                    "high": 3010 + index,
                    "low": 2990 + index,
                    "close": 3005 + index,
                    "vol": 100000,
                    "amount": 1000000,
                }
                for index, item in enumerate(self.trade_dates)
            ]
        raise AssertionError(f"Unexpected Tushare API: {api_name}")


class ScreenerApiTests(unittest.TestCase):
    def test_tushare_source_syncs_and_returns_only_top_50(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            app_root = Path(temp) / "oneil-screener"
            trade_dates: list[date] = []
            cursor = date(2025, 1, 1)
            while len(trade_dates) < 260:
                if cursor.weekday() < 5:
                    trade_dates.append(cursor)
                cursor += timedelta(days=1)
            service = TushareDataService(app_root, FakeTushareClient(trade_dates))
            status = service.sync(today=trade_dates[-1])
            self.assertTrue(status["ready"])
            self.assertEqual(status["stock_count"], 55)

            server = create_server(port=0, app_root=app_root, tushare_service=service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                state = request_json(
                    f"http://127.0.0.1:{server.server_port}",
                    "/api/scan",
                    "POST",
                    {"data_source": "tushare"},
                )
                self.assertEqual(len(state["results"]), 50)
                self.assertEqual(state["summary"]["total"], 50)
                self.assertEqual(state["summary"]["scanned_total"], 55)
                self.assertEqual(state["summary"]["result_limit"], 50)
                self.assertEqual(state["data_sources"]["active"], "tushare")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_scan_and_watchlist_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            app_root = Path(temp) / "oneil-screener"
            tdx_root = Path(temp) / "tdx"
            write_day_file(tdx_root / "vipdoc" / "sh" / "lday" / "sh000001.day", trend(3000, 2))
            write_day_file(tdx_root / "vipdoc" / "sh" / "lday" / "sh600001.day", trend(10, 0.08))
            write_day_file(tdx_root / "vipdoc" / "sz" / "lday" / "sz000001.day", trend(20, -0.03))
            write_day_file(tdx_root / "vipdoc" / "sz" / "lday" / "sz300001.day", trend(10, 0.12))

            server = create_server(port=0, app_root=app_root)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"

            try:
                state = request_json(
                    base_url,
                    "/api/scan",
                    "POST",
                    {"tdx_root": str(tdx_root), "auto_add": True},
                )
                self.assertEqual(state["summary"]["total"], 2)
                self.assertEqual(state["summary"]["watchlist"], 0)

                symbol = state["results"][0]["symbol"]
                state = request_json(base_url, "/api/watchlist", "POST", {"symbol": symbol})
                self.assertEqual(state["summary"]["watchlist"], 1)

                health = request_json(base_url, "/api/health")
                self.assertEqual(health["status"], "ok")
                self.assertEqual(health["results"], 2)

                state = request_json(base_url, f"/api/watchlist/{symbol}", "DELETE")
                self.assertEqual(state["summary"]["watchlist"], 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_smart_picks_reject_invalid_confidence(self) -> None:
        picker = FakeSmartPicker()
        picker.select = lambda candidates, tdx_root: {
            **FakeSmartPicker().select(candidates, tdx_root),
            "picks": [
                {**pick, "confidence": "高"}
                for pick in FakeSmartPicker().select(candidates, tdx_root)["picks"]
            ],
        }

        with tempfile.TemporaryDirectory() as temp:
            app_root = Path(temp) / "oneil-screener"
            tdx_root = Path(temp) / "tdx"
            write_day_file(tdx_root / "vipdoc" / "sh" / "lday" / "sh000001.day", trend(3000, 2))
            for index in range(1, 4):
                symbol = f"sh{600000 + index:06d}"
                write_day_file(
                    tdx_root / "vipdoc" / "sh" / "lday" / f"{symbol}.day",
                    trend(10 + index, 0.04),
                )

            server = create_server(port=0, app_root=app_root, smart_picker=picker)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with self.assertRaises(HTTPError) as context:
                    request_json(
                        f"http://127.0.0.1:{server.server_port}",
                        "/api/smart-picks",
                        "POST",
                        {"tdx_root": str(tdx_root)},
                    )
                self.assertEqual(context.exception.code, 400)
                context.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_smart_picks_scan_first_and_persist_three_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            app_root = Path(temp) / "oneil-screener"
            tdx_root = Path(temp) / "tdx"
            write_day_file(tdx_root / "vipdoc" / "sh" / "lday" / "sh000001.day", trend(3000, 2))
            for index in range(1, 11):
                symbol = f"sh{600000 + index:06d}"
                write_day_file(
                    tdx_root / "vipdoc" / "sh" / "lday" / f"{symbol}.day",
                    trend(10 + index, 0.03 + index * 0.005),
                )

            picker = FakeSmartPicker()
            server = create_server(port=0, app_root=app_root, smart_picker=picker)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"

            try:
                state = request_json(
                    base_url,
                    "/api/smart-picks",
                    "POST",
                    {"tdx_root": str(tdx_root)},
                )
                self.assertEqual(state["summary"]["total"], 10)
                self.assertEqual(state["summary"]["watchlist"], 0)
                self.assertEqual(state["summary"]["smart"], 3)
                self.assertEqual(len(picker.candidate_symbols), 10)
                self.assertEqual(state["smart_picks"]["model"], "fake-smart-model")
                self.assertTrue((app_root / "storage" / "smart_picks.json").exists())

                persisted = request_json(base_url, "/api/screener")
                self.assertEqual(len(persisted["smart_picks"]["picks"]), 3)
                self.assertEqual(
                    {item["symbol"] for item in persisted["smart_picks"]["picks"]},
                    set(picker.candidate_symbols[:3]),
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
