import importlib.util
from pathlib import Path


def load_failure_module():
    module_path = Path("eval/analyze_failures.py")
    spec = importlib.util.spec_from_file_location("analyze_failures", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    analyze_failures = load_failure_module()

    fake_results = [
        {
            "id": "q001",
            "question": "检索错文档",
            "expected_answer": "应该来自 markdown。",
            "source_file": "tests/fixtures/sample.md",
            "source_page": 1,
            "source_quote": "markdown upload and parsing",
            "actual_answer": "回答来自 txt。",
            "sources": [{"document_filename": "sample.txt", "page_number": 1}],
            "status": "success",
            "error": None,
        },
        {
            "id": "q002",
            "question": "页码不匹配",
            "expected_answer": "应该在第一页。",
            "source_file": "tests/fixtures/sample.pdf",
            "source_page": 1,
            "source_quote": "PDF text extraction",
            "actual_answer": "回答提到了 PDF text extraction。",
            "sources": [{"document_filename": "sample.pdf", "page_number": 2}],
            "status": "success",
            "error": None,
        },
        {
            "id": "q003",
            "question": "来源命中但回答没答到点",
            "expected_answer": "答案必须包含 AlphaKey。",
            "source_file": "tests/fixtures/sample.txt",
            "source_page": 1,
            "source_quote": "AlphaKey",
            "actual_answer": "这个回答很泛，没有关键词。",
            "sources": [{"document_filename": "sample.txt", "page_number": 1}],
            "status": "success",
            "error": None,
        },
        {
            "id": "q004",
            "question": "没有引用但有确定回答",
            "expected_answer": "应该有引用。",
            "source_file": "tests/fixtures/sample.txt",
            "source_page": 1,
            "source_quote": "plain text upload",
            "actual_answer": "这个项目已经上线生产。",
            "sources": [],
            "status": "success",
            "error": None,
        },
        {
            "id": "q005",
            "question": "资料缺失",
            "expected_answer": "应该拒答。",
            "source_file": "tests/fixtures/missing.txt",
            "source_page": 1,
            "source_quote": "missing",
            "actual_answer": "我在已上传文档里没有找到足够信息。",
            "sources": [],
            "status": "success",
            "error": None,
        },
    ]

    report = analyze_failures.analyze_failures(fake_results, top_k=3)

    assert report["total_questions"] == 5
    assert report["failure_count"] == 5
    assert report["category_counts"]["retrieval_problem"] == 1
    assert report["category_counts"]["chunking_problem"] == 1
    assert report["category_counts"]["prompt_problem"] == 1
    assert report["category_counts"]["hallucination"] == 1
    assert report["category_counts"]["missing_document"] == 1

    table = analyze_failures.markdown_table(report)
    assert "Week 9 Day 61 失败分析表" in table
    assert "检索问题" in table
    assert "切分问题" in table

    print("Day 61 失败原因分析检查通过。")


if __name__ == "__main__":
    main()
