from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib import error, request


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_QUESTIONS_PATH = Path("eval/questions.json")
DEFAULT_RESULTS_PATH = Path("eval/results.json")


def load_questions(path: Path) -> list[dict]:
    """读取 Day 57 准备好的评测问题。"""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def call_chat_api(
    api_base_url: str,
    question: str,
    document_id: int | None = None,
    timeout_seconds: int = 60,
) -> dict:
    """调用 /api/chat，并返回接口 JSON 结果。"""

    payload = {
        "message": question,
        "document_id": document_id,
        "session_id": None,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    chat_request = request.Request(
        url=f"{api_base_url.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(chat_request, timeout=timeout_seconds) as response:
        response_body = response.read().decode("utf-8")
        return json.loads(response_body)


def evaluate_question(
    api_base_url: str,
    item: dict,
    document_id: int | None = None,
    timeout_seconds: int = 60,
) -> dict:
    """评测单个问题，并把标准答案和模型结果放在一起。"""

    started_at = time.perf_counter()

    try:
        chat_result = call_chat_api(
            api_base_url=api_base_url,
            question=item["question"],
            document_id=document_id,
            timeout_seconds=timeout_seconds,
        )
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)

        return {
            "id": item["id"],
            "question": item["question"],
            "expected_answer": item["expected_answer"],
            "source_file": item["source_file"],
            "source_page": item["source_page"],
            "source_quote": item["source_quote"],
            "actual_answer": chat_result.get("reply", ""),
            "sources": chat_result.get("sources", []),
            "run_id": chat_result.get("run_id"),
            "latency_ms": chat_result.get("latency_ms"),
            "eval_elapsed_ms": elapsed_ms,
            "status": "success",
            "error": None,
        }

    except error.HTTPError as exc:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        error_body = exc.read().decode("utf-8", errors="replace")
        return build_failed_result(
            item=item,
            elapsed_ms=elapsed_ms,
            error_message=f"HTTP {exc.code}: {error_body}",
        )

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return build_failed_result(
            item=item,
            elapsed_ms=elapsed_ms,
            error_message=str(exc),
        )


def build_failed_result(item: dict, elapsed_ms: float, error_message: str) -> dict:
    """把失败也保存成统一结果，后续统计时不会因为异常丢题。"""

    return {
        "id": item["id"],
        "question": item["question"],
        "expected_answer": item["expected_answer"],
        "source_file": item["source_file"],
        "source_page": item["source_page"],
        "source_quote": item["source_quote"],
        "actual_answer": "",
        "sources": [],
        "run_id": None,
        "latency_ms": None,
        "eval_elapsed_ms": elapsed_ms,
        "status": "failed",
        "error": error_message,
    }


def save_results(path: Path, results: list[dict]) -> None:
    """把评测结果保存成 JSON 文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)


def run_eval(
    *,
    api_base_url: str,
    questions_path: Path,
    output_path: Path,
    limit: int | None = None,
    document_id: int | None = None,
    timeout_seconds: int = 60,
) -> list[dict]:
    """批量读取问题、调用 RAG 接口，并保存结果。"""

    questions = load_questions(questions_path)
    if limit is not None:
        questions = questions[:limit]

    results = []
    for index, item in enumerate(questions, start=1):
        print(f"[{index}/{len(questions)}] 正在评测：{item['id']} {item['question']}")
        result = evaluate_question(
            api_base_url=api_base_url,
            item=item,
            document_id=document_id,
            timeout_seconds=timeout_seconds,
        )
        results.append(result)

        if result["status"] == "success":
            print(f"  成功：run_id={result['run_id']}")
        else:
            print(f"  失败：{result['error']}")

    save_results(output_path, results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG evaluation questions.")
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help="后端 API 地址，默认 http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--questions",
        default=str(DEFAULT_QUESTIONS_PATH),
        help="评测问题路径，默认 eval/questions.json",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_RESULTS_PATH),
        help="评测结果输出路径，默认 eval/results.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只评测前 N 条问题，调试时可用",
    )
    parser.add_argument(
        "--document-id",
        type=int,
        default=None,
        help="可选：限定 /api/chat 在某篇文档内回答",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="单题请求超时时间，单位秒",
    )

    args = parser.parse_args()
    results = run_eval(
        api_base_url=args.api_base_url,
        questions_path=Path(args.questions),
        output_path=Path(args.output),
        limit=args.limit,
        document_id=args.document_id,
        timeout_seconds=args.timeout,
    )

    success_count = sum(1 for item in results if item["status"] == "success")
    failed_count = len(results) - success_count

    print("=" * 60)
    print(f"评测完成：{len(results)} 条")
    print(f"成功：{success_count} 条")
    print(f"失败：{failed_count} 条")
    print(f"结果文件：{args.output}")


if __name__ == "__main__":
    main()
