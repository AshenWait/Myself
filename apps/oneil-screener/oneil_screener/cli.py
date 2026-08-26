from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .scoring import score_universe
from .tdx import load_metadata_csv
from .watchlist import add_results, export_csv, load_watchlist, remove_symbol


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oneil-screen", description="Scan local Tongdaxin day data with an O'Neil style model.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Score stocks from local Tongdaxin data.")
    scan.add_argument("--tdx-root", required=True, type=Path, help="Tongdaxin root, for example C:\\new_tdx")
    scan.add_argument("--benchmark", default="sh000001", help="Benchmark day file symbol, default: sh000001")
    scan.add_argument("--metadata-csv", type=Path, help="Optional CSV with symbol,name,industry,eps_yoy,revenue_yoy,eps_3y_cagr,roe")
    scan.add_argument("--min-history", type=int, default=220, help="Minimum bars required per stock, default: 220")
    scan.add_argument("--limit-files", type=int, help="Debug/testing only: score at most N stock files")
    scan.add_argument("--top", type=int, default=50, help="Rows to print, default: 50")
    scan.add_argument("--output", type=Path, default=Path("output/oneil_scores.csv"), help="CSV output path")
    scan.add_argument("--json-output", type=Path, help="Optional JSON output path")
    scan.add_argument("--watchlist", type=Path, default=Path("storage/watchlist.json"), help="Watchlist JSON path")
    scan.add_argument("--auto-add", action="store_true", help="Add high-scoring rows into watchlist JSON")
    scan.add_argument("--min-score", type=float, default=75.0, help="Auto-add threshold, default: 75")
    scan.set_defaults(func=run_scan)

    watchlist = subparsers.add_parser("watchlist", help="Manage the saved watchlist.")
    watchlist_sub = watchlist.add_subparsers(dest="watchlist_command", required=True)
    list_cmd = watchlist_sub.add_parser("list", help="Print saved watchlist rows.")
    list_cmd.add_argument("--watchlist", type=Path, default=Path("storage/watchlist.json"))
    list_cmd.set_defaults(func=run_watchlist_list)
    remove_cmd = watchlist_sub.add_parser("remove", help="Remove one symbol from the watchlist.")
    remove_cmd.add_argument("symbol")
    remove_cmd.add_argument("--watchlist", type=Path, default=Path("storage/watchlist.json"))
    remove_cmd.set_defaults(func=run_watchlist_remove)
    export_cmd = watchlist_sub.add_parser("export", help="Export watchlist to CSV.")
    export_cmd.add_argument("--watchlist", type=Path, default=Path("storage/watchlist.json"))
    export_cmd.add_argument("--output", type=Path, default=Path("output/watchlist.csv"))
    export_cmd.set_defaults(func=run_watchlist_export)
    return parser


def run_scan(args: argparse.Namespace) -> int:
    metadata = load_metadata_csv(args.metadata_csv)
    results = score_universe(
        tdx_root=args.tdx_root,
        benchmark_symbol=args.benchmark,
        metadata=metadata,
        min_history=args.min_history,
        limit_files=args.limit_files,
    )
    write_scores_csv(args.output, results)
    if args.json_output:
        write_scores_json(args.json_output, results)
    added = 0
    if args.auto_add:
        added = add_results(args.watchlist, results, args.min_score)

    print(f"Scored {len(results)} stocks. CSV: {args.output}")
    if args.json_output:
        print(f"JSON: {args.json_output}")
    if args.auto_add:
        print(f"Watchlist: {args.watchlist} (newly added: {added}, threshold: {args.min_score})")
    print_table(results[: args.top])
    return 0


def write_scores_csv(path: Path, results: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "rank",
        "symbol",
        "name",
        "industry",
        "score",
        "bucket",
        "trade_date",
        "close",
        "rs_rank",
        "trend_score",
        "leader_score",
        "volume_score",
        "new_high_score",
        "market_score",
        "fundamental_score",
        "reasons",
        "flags",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "rank": item.rank,
                    "symbol": item.symbol,
                    "name": item.name,
                    "industry": item.industry,
                    "score": item.score,
                    "bucket": item.bucket,
                    "trade_date": item.trade_date,
                    "close": item.close,
                    "rs_rank": item.metrics.get("rs_rank", ""),
                    "trend_score": item.components.get("trend", ""),
                    "leader_score": item.components.get("leader", ""),
                    "volume_score": item.components.get("volume", ""),
                    "new_high_score": item.components.get("new_high", ""),
                    "market_score": item.components.get("market", ""),
                    "fundamental_score": item.components.get("fundamental", ""),
                    "reasons": ";".join(item.reasons),
                    "flags": ";".join(item.flags),
                }
            )


def write_scores_json(path: Path, results: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(item) for item in results], handle, ensure_ascii=False, indent=2)


def print_table(results: list) -> None:
    if not results:
        print("No rows.")
        return
    print("rank symbol    score bucket                         close date")
    for item in results:
        print(f"{item.rank:>4} {item.symbol:<8} {item.score:>5.1f} {item.bucket:<30} {item.close:>8.2f} {item.trade_date}")


def run_watchlist_list(args: argparse.Namespace) -> int:
    items = sorted(load_watchlist(args.watchlist).values(), key=lambda item: item.get("score", 0), reverse=True)
    print_table([SimpleRow(item, index + 1) for index, item in enumerate(items)])
    return 0


def run_watchlist_remove(args: argparse.Namespace) -> int:
    removed = remove_symbol(args.watchlist, args.symbol)
    print("Removed." if removed else "Symbol not found.")
    return 0


def run_watchlist_export(args: argparse.Namespace) -> int:
    count = export_csv(args.watchlist, args.output)
    print(f"Exported {count} rows to {args.output}")
    return 0


class SimpleRow:
    def __init__(self, item: dict, rank: int):
        self.rank = rank
        self.symbol = item.get("symbol", "")
        self.score = item.get("score", 0)
        self.bucket = item.get("bucket", "")
        self.close = item.get("close", 0)
        self.trade_date = item.get("trade_date", "")


if __name__ == "__main__":
    raise SystemExit(main())
