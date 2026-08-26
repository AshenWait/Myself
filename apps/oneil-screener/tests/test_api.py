from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from oneil_screener.api import create_server
from oneil_screener.tdx import DAY_RECORD


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


class ScreenerApiTests(unittest.TestCase):
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
                    {"tdx_root": str(tdx_root), "auto_add": False},
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


if __name__ == "__main__":
    unittest.main()
