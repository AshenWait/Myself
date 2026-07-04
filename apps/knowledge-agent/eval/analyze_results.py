from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_RESULTS_PATH = Path("eval/results.json")
DEFAULT_REPORT_PATH = Path("eval/report.json")


def load_results(path: Path) -> list[dict[str, Any]]:
    """读取 Day 58 生成的评测结果。"""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_report(path: Path, report: dict[str, Any]) -> None:
    """保存 Day 59 的检索命中率分析报告。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)


def expected_filename(result: dict[str, Any]) -> str:
    """从标准来源路径中取文件名。"""

    return Path(str(result["source_file"])).name


def source_filename(source: dict[str, Any]) -> str:
    """从接口返回的 source 中取文件名。"""

    if source.get("document_filename"):
        return Path(str(source["document_filename"])).name
    if source.get("source_file"):
        return Path(str(source["source_file"])).name
    return ""


def source_page(source: dict[str, Any]) -> int | None:
    """从接口返回的 source 中取页码。"""

    page = source.get("page_number", source.get("source_page"))
    if page is None:
        return None
    return int(page)


def is_source_hit(result: dict[str, Any], source: dict[str, Any]) -> bool:
    """判断某个 source 是否命中标准来源。"""

    return (
        source_filename(source) == expected_filename(result)
        and source_page(source) == int(result["source_page"])
    )


def has_top_k_hit(result: dict[str, Any], top_k: int) -> bool:
    """判断标准来源是否出现在前 top_k 个 sources 中。"""

    top_sources = result.get("sources", [])[:top_k]
    return any(is_source_hit(result, source) for source in top_sources)


def classify_miss_reason(result: dict[str, Any], top_k: int) -> str:
    """给未命中的问题做简单失败分类。"""

    if result.get("status") != "success":
        return "api_failed"

    sources = result.get("sources", [])
    if not sources:
        return "no_sources"

    top_sources = sources[:top_k]
    expected_file = expected_filename(result)
    expected_page = int(result["source_page"])

    filenames = {source_filename(source) for source in top_sources}
    pages_for_expected_file = {
        source_page(source)
        for source in top_sources
        if source_filename(source) == expected_file
    }

    if expected_file not in filenames:
        return "wrong_document"

    if expected_page not in pages_for_expected_file:
        return "page_mismatch"

    return "source_metadata_mismatch"


def analyze_results(results: list[dict[str, Any]], top_k: int = 3) -> dict[str, Any]:
    """计算 top-k 命中率，并列出没有命中的问题。"""

    total = len(results)
    successful_results = [
        result for result in results if result.get("status") == "success"
    ]

    hit_items = []
    missed_items = []
    reason_counter: Counter[str] = Counter()

    for result in results:
        if has_top_k_hit(result, top_k=top_k):
            hit_items.append(result)
            continue

        reason = classify_miss_reason(result, top_k=top_k)
        reason_counter[reason] += 1
        missed_items.append(
            {
                "id": result["id"],
                "question": result["question"],
                "expected_source_file": result["source_file"],
                "expected_source_page": result["source_page"],
                "top_sources": result.get("sources", [])[:top_k],
                "reason": reason,
                "error": result.get("error"),
            }
        )

    hit_count = len(hit_items)
    hit_rate = hit_count / total if total else 0.0

    return {
        "top_k": top_k,
        "total_questions": total,
        "successful_questions": len(successful_results),
        "failed_questions": total - len(successful_results),
        "top_k_hit_count": hit_count,
        "top_k_hit_rate": round(hit_rate, 4),
        "missed_count": len(missed_items),
        "miss_reasons": dict(reason_counter),
        "missed_questions": missed_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze RAG evaluation results.")
    parser.add_argument(
        "--results",
        default=str(DEFAULT_RESULTS_PATH),
        help="Day 58 生成的结果文件，默认 eval/results.json",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REPORT_PATH),
        help="分析报告输出路径，默认 eval/report.json",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="计算 top-k 检索命中率，默认 top-3",
    )
    args = parser.parse_args()

    results = load_results(Path(args.results))
    report = analyze_results(results, top_k=args.top_k)
    save_report(Path(args.output), report)

    print("=" * 60)
    print(f"总问题数：{report['total_questions']}")
    print(f"成功回答数：{report['successful_questions']}")
    print(f"接口失败数：{report['failed_questions']}")
    print(f"top-{report['top_k']} 命中数：{report['top_k_hit_count']}")
    print(f"top-{report['top_k']} 命中率：{report['top_k_hit_rate']}")
    print(f"未命中数：{report['missed_count']}")
    print(f"失败原因：{report['miss_reasons']}")
    print(f"报告文件：{args.output}")


if __name__ == "__main__":
    main()
