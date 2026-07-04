import importlib.util
import json
import tempfile
from pathlib import Path


def load_eval_module():
    module_path = Path("eval/run_rag_eval.py")
    spec = importlib.util.spec_from_file_location("run_rag_eval", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    run_rag_eval = load_eval_module()

    calls = []

    def fake_call_chat_api(api_base_url, question, document_id=None, timeout_seconds=60):
        calls.append(
            {
                "api_base_url": api_base_url,
                "question": question,
                "document_id": document_id,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "reply": f"模拟回答：{question}",
            "sources": [
                {
                    "document_filename": "sample.txt",
                    "page_number": 1,
                    "content": "This file is used to verify plain text upload and parsing.",
                }
            ],
            "run_id": "run-eval-test",
            "latency_ms": 123,
        }

    run_rag_eval.call_chat_api = fake_call_chat_api

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "results.json"
        results = run_rag_eval.run_eval(
            api_base_url="http://testserver",
            questions_path=Path("eval/questions.json"),
            output_path=output_path,
            limit=2,
            document_id=None,
            timeout_seconds=5,
        )

        saved_results = json.loads(output_path.read_text(encoding="utf-8"))

    assert len(calls) == 2
    assert len(results) == 2
    assert len(saved_results) == 2
    assert saved_results[0]["id"] == "q001"
    assert saved_results[0]["status"] == "success"
    assert saved_results[0]["actual_answer"].startswith("模拟回答")
    assert saved_results[0]["sources"][0]["page_number"] == 1
    assert saved_results[0]["run_id"] == "run-eval-test"

    failed_result = run_rag_eval.build_failed_result(
        item={
            "id": "q-error",
            "question": "错误问题",
            "expected_answer": "标准答案",
            "source_file": "tests/fixtures/sample.txt",
            "source_page": 1,
            "source_quote": "quote",
        },
        elapsed_ms=10.5,
        error_message="connection refused",
    )
    assert failed_result["status"] == "failed"
    assert failed_result["error"] == "connection refused"
    assert failed_result["sources"] == []

    print("Day 58 批量评测脚本检查通过。")


if __name__ == "__main__":
    main()
