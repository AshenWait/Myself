from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_BEFORE_PATH = Path("eval/report.before.json")
DEFAULT_AFTER_PATH = Path("eval/report.after.json")
DEFAULT_FAILURE_PATH = Path("eval/failure_analysis.json")
DEFAULT_OUTPUT_PATH = Path("eval/optimization_report.json")

BASELINE_CONFIG = {
    "rag_chunk_size": 500,
    "rag_chunk_overlap": 50,
    "rag_top_k": 3,
    "max_rag_distance": 0.8,
}

RECOMMENDED_CONFIG = {
    "rag_chunk_size": 700,
    "rag_chunk_overlap": 80,
    "rag_top_k": 5,
    "max_rag_distance": 0.85,
}


def load_json(path: Path) -> dict[str, Any]:
    """读取 JSON 文件。"""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: dict[str, Any]) -> None:
    """保存 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def metric_value(report: dict[str, Any], key: str) -> float | None:
    """安全读取指标值。"""

    value = report.get(key)
    if value is None:
        return None
    return float(value)


def compare_metric(
    before: dict[str, Any],
    after: dict[str, Any],
    key: str,
) -> dict[str, float | None]:
    """比较单个指标的前后变化。"""

    before_value = metric_value(before, key)
    after_value = metric_value(after, key)

    if before_value is None or after_value is None:
        delta = None
    else:
        delta = round(after_value - before_value, 4)

    return {
        "before": before_value,
        "after": after_value,
        "delta": delta,
    }


def recommendations_from_failures(failure_report: dict[str, Any]) -> list[dict[str, str]]:
    """根据 Day 61 失败分类生成参数优化建议。"""

    counts = failure_report.get("category_counts", {})
    recommendations = []

    if counts.get("chunking_problem", 0) > 0:
        recommendations.append(
            {
                "target": "chunk_size / overlap",
                "suggestion": "提高 overlap 或适度增大 chunk_size，减少答案跨 chunk 被切断的情况。",
                "reason": "失败分析中出现切分问题。",
            }
        )

    if counts.get("retrieval_problem", 0) > 0:
        recommendations.append(
            {
                "target": "top_k / score threshold",
                "suggestion": "把 top_k 从 3 提升到 5，并把 max_rag_distance 从 0.8 放宽到 0.85 后重新评测。",
                "reason": "失败分析中出现检索问题，正确来源可能没有进入前 3 或被阈值过滤。",
            }
        )

    if counts.get("missing_document", 0) > 0:
        recommendations.append(
            {
                "target": "document ingestion",
                "suggestion": "先确认文档已上传、解析、切分、embedding 入库，再比较检索参数。",
                "reason": "文档缺失不是调参能直接解决的问题。",
            }
        )

    if counts.get("prompt_problem", 0) > 0 or counts.get("hallucination", 0) > 0:
        recommendations.append(
            {
                "target": "prompt / output guardrails",
                "suggestion": "强化 prompt 的引用约束，并保留无引用确定性回答的输出检查。",
                "reason": "来源命中后回答仍偏离，或无来源却给出确定性回答。",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "target": "keep current config",
                "suggestion": "当前失败分析没有暴露明确参数问题，先保留配置并扩大评测集。",
                "reason": "没有足够证据说明调参会提升指标。",
            }
        )

    return recommendations


def build_optimization_report(
    *,
    before_report: dict[str, Any] | None = None,
    after_report: dict[str, Any] | None = None,
    failure_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """生成 Day 62 的参数对比和优化建议报告。"""

    before_report = before_report or {}
    after_report = after_report or {}
    failure_report = failure_report or {"category_counts": {}}

    metric_comparison = {
        "top_k_hit_rate": compare_metric(before_report, after_report, "top_k_hit_rate"),
        "citation_rate": compare_metric(before_report, after_report, "citation_rate"),
    }

    return {
        "config_before": BASELINE_CONFIG,
        "config_candidate": RECOMMENDED_CONFIG,
        "metric_comparison": metric_comparison,
        "recommendations": recommendations_from_failures(failure_report),
        "notes": [
            "只有真实运行 before/after 评测后，metric_comparison 才代表实际提升。",
            "不要只因为参数看起来更大就认为效果更好，必须用同一批 eval/questions.json 对比。",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare RAG optimization metrics.")
    parser.add_argument("--before", default=str(DEFAULT_BEFORE_PATH))
    parser.add_argument("--after", default=str(DEFAULT_AFTER_PATH))
    parser.add_argument("--failures", default=str(DEFAULT_FAILURE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    before_path = Path(args.before)
    after_path = Path(args.after)
    failure_path = Path(args.failures)

    before_report = load_json(before_path) if before_path.exists() else None
    after_report = load_json(after_path) if after_path.exists() else None
    failure_report = load_json(failure_path) if failure_path.exists() else None

    report = build_optimization_report(
        before_report=before_report,
        after_report=after_report,
        failure_report=failure_report,
    )
    save_json(Path(args.output), report)

    print("=" * 60)
    print("候选配置:", report["config_candidate"])
    print("指标对比:", report["metric_comparison"])
    print("建议数量:", len(report["recommendations"]))
    print(f"报告文件：{args.output}")


if __name__ == "__main__":
    main()
