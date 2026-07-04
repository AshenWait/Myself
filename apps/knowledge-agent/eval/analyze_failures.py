from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_RESULTS_PATH = Path("eval/results.json")
DEFAULT_OUTPUT_PATH = Path("eval/failure_analysis.json")
DEFAULT_TABLE_PATH = Path("docs/week9-failure-analysis.md")

CATEGORY_LABELS = {
    "chunking_problem": "切分问题",
    "retrieval_problem": "检索问题",
    "prompt_problem": "prompt 问题",
    "hallucination": "模型幻觉",
    "missing_document": "文档缺失",
}


def load_results(path: Path) -> list[dict[str, Any]]:
    """读取 Day 58 生成的评测结果。"""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: dict[str, Any]) -> None:
    """保存失败分析 JSON。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def expected_filename(result: dict[str, Any]) -> str:
    """从标准来源路径中取文件名。"""

    return Path(str(result["source_file"])).name


def source_filename(source: dict[str, Any]) -> str:
    """从 sources 中提取文件名。"""

    if source.get("document_filename"):
        return Path(str(source["document_filename"])).name
    if source.get("source_file"):
        return Path(str(source["source_file"])).name
    return ""


def source_page(source: dict[str, Any]) -> int | None:
    """从 sources 中提取页码。"""

    page = source.get("page_number", source.get("source_page"))
    if page is None:
        return None
    return int(page)


def source_summary(sources: list[dict[str, Any]], top_k: int = 3) -> str:
    """生成适合放进 Markdown 表格的来源摘要。"""

    if not sources:
        return "无"

    items = []
    for source in sources[:top_k]:
        filename = source_filename(source) or "未知文件"
        page = source_page(source)
        page_text = f"p{page}" if page is not None else "未知页"
        items.append(f"{filename}:{page_text}")
    return "<br>".join(items)


def extract_keywords(text: str) -> set[str]:
    """抽取用于粗略判断答案覆盖度的关键词。"""

    english_tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text)
    }
    chinese_tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}", text))
    return english_tokens | chinese_tokens


def answer_mentions_expected(result: dict[str, Any]) -> bool:
    """判断实际回答是否覆盖了标准答案或引用中的关键词。"""

    answer = str(result.get("actual_answer") or "").lower()
    expected_text = f"{result.get('expected_answer', '')} {result.get('source_quote', '')}"
    keywords = extract_keywords(expected_text)

    if not keywords:
        return bool(answer.strip())

    return any(keyword.lower() in answer for keyword in keywords)


def classify_failure(result: dict[str, Any], top_k: int = 3) -> tuple[str | None, str]:
    """把一条失败或低质量结果归类到 Day 61 的失败类型。"""

    if result.get("status") != "success":
        error = str(result.get("error") or "")
        if any(keyword in error for keyword in ["文档不存在", "document", "404"]):
            return "missing_document", "接口失败且错误信息指向文档不存在或文档缺失"
        return "retrieval_problem", "接口失败，无法完成检索或问答流程"

    sources = result.get("sources", [])
    answer = str(result.get("actual_answer") or "").strip()

    if not sources:
        if "没有找到" in answer or "not found" in answer.lower():
            return "missing_document", "回答表示没有找到资料，且没有返回引用来源"
        if answer:
            return "hallucination", "有确定性回答，但 sources 为空"
        return "retrieval_problem", "没有回答，也没有返回引用来源"

    expected_file = expected_filename(result)
    expected_page = int(result["source_page"])
    top_sources = sources[:top_k]
    same_file_sources = [
        source for source in top_sources if source_filename(source) == expected_file
    ]

    if not same_file_sources:
        return "retrieval_problem", "top-k 来源没有命中标准文档"

    if all(source_page(source) != expected_page for source in same_file_sources):
        return "chunking_problem", "命中了标准文档，但页码或切分边界不匹配"

    if not answer_mentions_expected(result):
        return "prompt_problem", "来源命中，但回答没有覆盖标准答案关键词"

    return None, "命中标准来源，暂不归为失败"


def suggested_action(category: str) -> str:
    """给每类失败提供下一步排查建议。"""

    actions = {
        "chunking_problem": "检查 chunk_size、overlap 和页码保留逻辑",
        "retrieval_problem": "检查 query、top_k、score threshold 和 embedding 覆盖",
        "prompt_problem": "强化 RAG prompt，要求围绕引用回答",
        "hallucination": "加强输出检查，禁止无引用确定性回答",
        "missing_document": "确认文档是否上传、解析、入库并生成 embedding",
    }
    return actions[category]


def analyze_failures(
    results: list[dict[str, Any]],
    top_k: int = 3,
) -> dict[str, Any]:
    """统计失败原因，并生成失败分析表数据。"""

    rows = []
    counter: Counter[str] = Counter()

    for result in results:
        category, reason = classify_failure(result, top_k=top_k)
        if category is None:
            continue

        counter[category] += 1
        rows.append(
            {
                "id": result["id"],
                "question": result["question"],
                "category": category,
                "category_label": CATEGORY_LABELS[category],
                "reason": reason,
                "expected_source": f"{result['source_file']}#page={result['source_page']}",
                "top_sources": source_summary(result.get("sources", []), top_k=top_k),
                "suggested_action": suggested_action(category),
            }
        )

    return {
        "top_k": top_k,
        "total_questions": len(results),
        "failure_count": len(rows),
        "category_counts": dict(counter),
        "failure_rows": rows,
    }


def markdown_table(report: dict[str, Any]) -> str:
    """把失败分析结果转成 Markdown 表格。"""

    lines = [
        "# Week 9 Day 61 失败分析表",
        "",
        f"- 总问题数：{report['total_questions']}",
        f"- 失败或低质量结果数：{report['failure_count']}",
        f"- 分类统计：`{json.dumps(report['category_counts'], ensure_ascii=False)}`",
        "",
        "| ID | 问题 | 分类 | 原因 | 标准来源 | top 来源 | 建议动作 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in report["failure_rows"]:
        lines.append(
            "| {id} | {question} | {category_label} | {reason} | {expected_source} | {top_sources} | {suggested_action} |".format(
                **row
            )
        )

    return "\n".join(lines) + "\n"


def save_markdown_table(path: Path, report: dict[str, Any]) -> None:
    """保存 Markdown 失败分析表。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown_table(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze RAG failure reasons.")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--table", default=str(DEFAULT_TABLE_PATH))
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    results = load_results(Path(args.results))
    report = analyze_failures(results, top_k=args.top_k)
    save_json(Path(args.output), report)
    save_markdown_table(Path(args.table), report)

    print("=" * 60)
    print(f"总问题数：{report['total_questions']}")
    print(f"失败或低质量结果数：{report['failure_count']}")
    print(f"分类统计：{report['category_counts']}")
    print(f"JSON 报告：{args.output}")
    print(f"分析表：{args.table}")


if __name__ == "__main__":
    main()
