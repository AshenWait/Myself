import importlib.util
import json
import tempfile
from pathlib import Path


def load_analysis_module():
    module_path = Path("eval/analyze_results.py")
    spec = importlib.util.spec_from_file_location("analyze_results", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    analyze_results = load_analysis_module()

    fake_results = [
        {
            "id": "q001",
            "question": "sample.txt 是用来验证什么的？",
            "expected_answer": "sample.txt 用来验证纯文本文件上传和解析。",
            "source_file": "tests/fixtures/sample.txt",
            "source_page": 1,
            "actual_answer": "它用于验证纯文本上传和解析。",
            "sources": [
                {
                    "document_filename": "sample.txt",
                    "page_number": 1,
                    "content": "plain text upload and parsing",
                }
            ],
            "status": "success",
            "error": None,
        },
        {
            "id": "q002",
            "question": "sample.md 是用来验证什么的？",
            "expected_answer": "sample.md 用来验证 markdown 上传和解析。",
            "source_file": "tests/fixtures/sample.md",
            "source_page": 1,
            "actual_answer": "它用于验证 markdown。",
            "sources": [
                {
                    "document_filename": "sample.txt",
                    "page_number": 1,
                    "content": "plain text upload and parsing",
                }
            ],
            "status": "success",
            "error": None,
        },
        {
            "id": "q003",
            "question": "sample.pdf 是用来验证什么的？",
            "expected_answer": "sample.pdf 用来验证 PDF 文本抽取。",
            "source_file": "tests/fixtures/sample.pdf",
            "source_page": 1,
            "actual_answer": "",
            "sources": [],
            "status": "failed",
            "error": "connection refused",
        },
    ]

    report = analyze_results.analyze_results(fake_results, top_k=3)

    assert report["total_questions"] == 3
    assert report["successful_questions"] == 2
    assert report["failed_questions"] == 1
    assert report["top_k_hit_count"] == 1
    assert report["top_k_hit_rate"] == 0.3333
    assert report["missed_count"] == 2
    assert report["miss_reasons"]["wrong_document"] == 1
    assert report["miss_reasons"]["api_failed"] == 1

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "report.json"
        analyze_results.save_report(output_path, report)
        saved_report = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved_report["top_k_hit_count"] == 1
    assert saved_report["missed_questions"][0]["id"] == "q002"

    print("Day 59 检索命中率分析检查通过。")


if __name__ == "__main__":
    main()
