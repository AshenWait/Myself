from app.services.output_guardrails import (
    build_output_refusal,
    check_answer_output,
    log_output_check,
)


def main() -> None:
    safe_result = check_answer_output(
        answer="根据资料内容，项目已经实现了工具调用。",
        sources=[
            {
                "chunk_id": 1,
                "document_id": 1,
                "content": "项目已经实现了工具调用。",
            }
        ],
    )
    assert safe_result.allowed is True

    refusal_result = check_answer_output(
        answer="我在已上传文档里没有找到足够信息。",
        sources=[],
    )
    assert refusal_result.allowed is True

    risky_result = check_answer_output(
        answer="这个项目一定已经上线生产环境。",
        sources=[],
    )
    assert risky_result.allowed is False
    assert risky_result.risk_level == "high"
    assert risky_result.reasons

    refusal = build_output_refusal(risky_result)
    assert "没有引用来源" in refusal

    log = log_output_check(
        db=None,
        question="项目是否上线？",
        answer="这个项目一定已经上线生产环境。",
        result=risky_result,
    )
    assert log is None

    print("有来源回答检查通过:", safe_result)
    print("无来源拒答检查通过:", refusal_result)
    print("无来源答案被正确拦截:", risky_result)
    print("Day 47 输出 Guardrails 检查通过。")


if __name__ == "__main__":
    main()
