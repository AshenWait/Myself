from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from oneil_screener.scoring import score_universe
from oneil_screener.tdx import DAY_RECORD
from oneil_screener.watchlist import add_results, export_csv, remove_symbol


def write_day_file(path: Path, prices: list[float], start: date = date(2025, 1, 1), volume_base: int = 10000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for index, close in enumerate(prices):
            trade_date = start + timedelta(days=index)
            raw_date = trade_date.year * 10000 + trade_date.month * 100 + trade_date.day
            cents = int(round(close * 100))
            volume = volume_base + index * 100
            handle.write(DAY_RECORD.pack(raw_date, cents, cents + 10, cents - 10, cents, float(cents * volume), volume, 0))


def trend(start: float, step: float, days: int = 260) -> list[float]:
    return [round(start + step * index, 2) for index in range(days)]


class ScoringAndWatchlistTests(unittest.TestCase):
    def test_scores_and_persists_high_ranked_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_day_file(root / "vipdoc" / "sh" / "lday" / "sh000001.day", trend(3000, 2))
            write_day_file(root / "vipdoc" / "sh" / "lday" / "sh600001.day", trend(10, 0.08), volume_base=20000)
            write_day_file(root / "vipdoc" / "sz" / "lday" / "sz000001.day", trend(20, -0.03), volume_base=10000)
            write_day_file(root / "vipdoc" / "sz" / "lday" / "sz300001.day", trend(10, 0.12), volume_base=30000)

            results = score_universe(root)

            self.assertGreaterEqual(len(results), 2)
            self.assertEqual(results[0].symbol, "sh600001")
            self.assertNotIn("sz300001", {result.symbol for result in results})
            self.assertGreater(results[0].score, results[-1].score)

            watchlist = root / "storage" / "watchlist.json"
            added = add_results(watchlist, results, min_score=70)
            self.assertGreaterEqual(added, 1)

            payload = json.loads(watchlist.read_text(encoding="utf-8"))
            saved_symbols = {item["symbol"] for item in payload["items"]}
            self.assertIn("sh600001", saved_symbols)

            exported = root / "output" / "watchlist.csv"
            count = export_csv(watchlist, exported)
            self.assertEqual(count, len(payload["items"]))
            self.assertTrue(exported.exists())

            self.assertTrue(remove_symbol(watchlist, "600001"))


if __name__ == "__main__":
    unittest.main()
