import importlib.util
from pathlib import Path


def load_optimization_module():
    module_path = Path("eval/compare_optimization.py")
    spec = importlib.util.spec_from_file_location("compare_optimization", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    compare_optimization = load_optimization_module()

    before_report = {
        "top_k_hit_rate": 0.5,
        "citation_rate": 0.7,
    }
    after_report = {
        "top_k_hit_rate": 0.7,
        "citation_rate": 0.8,
    }
    failure_report = {
        "category_counts": {
            "chunking_problem": 2,
            "retrieval_problem": 3,
            "prompt_problem": 1,
            "hallucination": 1,
            "missing_document": 1,
        }
    }

    report = compare_optimization.build_optimization_report(
        before_report=before_report,
        after_report=after_report,
        failure_report=failure_report,
    )

    assert report["config_before"]["rag_top_k"] == 3
    assert report["config_candidate"]["rag_top_k"] == 5
    assert report["metric_comparison"]["top_k_hit_rate"]["delta"] == 0.2
    assert report["metric_comparison"]["citation_rate"]["delta"] == 0.1

    targets = {item["target"] for item in report["recommendations"]}
    assert "chunk_size / overlap" in targets
    assert "top_k / score threshold" in targets
    assert "prompt / output guardrails" in targets
    assert "document ingestion" in targets

    print("Day 62 参数优化对比检查通过。")


if __name__ == "__main__":
    main()
