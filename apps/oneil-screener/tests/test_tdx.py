from __future__ import annotations

import struct
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from oneil_screener.tdx import DAY_RECORD, TNF_HEADER_SIZE, TNF_NAME_OFFSET, TNF_RECORD_SIZE, iter_stock_day_files, load_tdx_stock_names, read_day_file


def write_day_file(path: Path, prices: list[float], start: date = date(2025, 1, 1)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for index, close in enumerate(prices):
            trade_date = start + timedelta(days=index)
            raw_date = trade_date.year * 10000 + trade_date.month * 100 + trade_date.day
            cents = int(round(close * 100))
            handle.write(DAY_RECORD.pack(raw_date, cents, cents + 10, cents - 10, cents, float(cents * 1000), 10000 + index, 0))


def write_name_file(path: Path, rows: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = bytearray(TNF_HEADER_SIZE)
    for code, name in rows:
        record = bytearray(TNF_RECORD_SIZE)
        record[:6] = code.encode("ascii")
        encoded_name = name.encode("gbk")
        record[TNF_NAME_OFFSET : TNF_NAME_OFFSET + len(encoded_name)] = encoded_name
        payload.extend(record)
    path.write_bytes(payload)


class TongdaxinReaderTests(unittest.TestCase):
    def test_load_tdx_stock_names_reads_current_tnf_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_name_file(root / "T0002" / "hq_cache" / "shs.tnf", [("603268", "松发股份")])
            write_name_file(root / "T0002" / "hq_cache" / "szs.tnf", [("002412", "汉森制药")])

            names = load_tdx_stock_names(root)

            self.assertEqual(names["sh603268"], "松发股份")
            self.assertEqual(names["sz002412"], "汉森制药")

    def test_read_day_file_decodes_prices(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "vipdoc" / "sh" / "lday" / "sh600000.day"
            write_day_file(path, [10.0, 10.5, 11.0])

            series = read_day_file(path)

            self.assertEqual(series.symbol, "sh600000")
            self.assertEqual(len(series.bars), 3)
            self.assertEqual(series.bars[-1].trade_date, date(2025, 1, 3))
            self.assertEqual(series.bars[-1].close, 11.0)

    def test_iter_stock_day_files_skips_indices(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_day_file(root / "vipdoc" / "sh" / "lday" / "sh600000.day", [10.0])
            write_day_file(root / "vipdoc" / "sh" / "lday" / "sh000001.day", [10.0])
            write_day_file(root / "vipdoc" / "sz" / "lday" / "sz300001.day", [10.0])
            write_day_file(root / "vipdoc" / "sz" / "lday" / "sz399001.day", [10.0])

            symbols = [symbol for symbol, _ in iter_stock_day_files(root)]

            self.assertEqual(symbols, ["sh600000", "sz300001"])


if __name__ == "__main__":
    unittest.main()
