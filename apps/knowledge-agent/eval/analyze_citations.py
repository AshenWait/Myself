from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_RESULTS_PATH = Path("eval/results.json")
DEFAULT_REPORT_PATH = Path("eval/citation_report.json")


def load_results(path: Path) -> list[dict[str, Any]]:
    """读取 Day 58 生成的评测结果。"""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_report(path: Path, report: dict[str, Any]) -> None:
    """保存引用完整率分析报告。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)


def has_citation(result: dict[str, Any]) -> bool:
    """判断一条评测结果是否有引用来源。"""

    sources = result.get("sources", [])
    return result.get("status") == "success" and len(sources) > 0


def classify_citation_issue(result: dict[str, Any]) -> str:
    """给没有引用的回答分类。"""

    if result.get("status") != "success":
        return "api_failed"

    actual_answer = (result.get("actual_answer") or "").strip()
    sources = result.get("sources", [])

    if not actual_answer:
        return "empty_answer"

    if not sources:
        return "missing_sources"

    return "unknown"


def analyze_citations(results: list[dict[str, Any]]) -> dict[str, Any]:
    """计算引用完整率，并列出没有引用的问题。"""

    total = len(results)
    cited_results = []
    missing_citation_results = []
    reason_counts: dict[str, int] = {}

    for result in results:
        if has_citation(result):
            cited_results.append(result)
            continue

        reason = classify_citation_issue(result)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        missing_citation_results.append(
            {
                "id": result["id"],
                "question": result["question"],
                "expected_answer": result["expected_answer"],
                "actual_answer": result.get("actual_answer", ""),
                "source_file": result["source_file"],
                "source_page": result["source_page"],
                "status": result.get("status"),
                "error": result.get("error"),
                "reason": reason,
            }
        )

    citation_count = len(cited_results)
    citation_rate = citation_count / total if total else 0.0

    return {
        "total_questions": total,
        "citation_count": citation_count,
        "missing_citation_count": len(missing_citation_results),
        "citation_rate": round(citation_rate, 4),
        "issue_reasons": reason_counts,
        "missing_citation_questions": missing_citation_results,
        "prompt_or_guardrail_action": suggest_prompt_or_guardrail_action(reason_counts),
    }


def suggest_prompt_or_guardrail_action(reason_counts: dict[str, int]) -> str:
    """根据引用缺失情况给出 prompt 或输出检查建议。"""

    if reason_counts.get("missing_sources", 0) > 0:
        return "保留输出检查：成功回答但 sources 为空时，应拒答或要求重新生成。"

    if reason_counts.get("empty_answer", 0) > 0:
        return "检查 RAG prompt 和模型调用，避免空回答。"

    if reason_counts.get("api_failed", 0) > 0:
        return "先修复接口或依赖错误，再判断 prompt 是否需要调整。"

    return "当前引用完整率没有暴露必须修改 prompt 或输出检查的问题。"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze RAG citation completeness.")
    parser.add_argument(
        "--results",
        default=str(DEFAULT_RESULTS_PATH),
        help="Day 58 生成的结果文件，默认 eval/results.json",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REPORT_PATH),
        help="引用分析报告输出路径，默认 eval/citation_report.json",
    )
    args = parser.parse_args()

    results = load_results(Path(args.results))
    report = analyze_citations(results)
    save_report(Path(args.output), report)

    print("=" * 60)
    print(f"总问题数：{report['total_questions']}")
    print(f"有引用回答数：{report['citation_count']}")
    print(f"无引用回答数：{report['missing_citation_count']}")
    print(f"引用完整率：{report['citation_rate']}")
    print(f"问题原因：{report['issue_reasons']}")
    print(f"建议动作：{report['prompt_or_guardrail_action']}")
    print(f"报告文件：{args.output}")


if __name__ == "__main__":
    main()
