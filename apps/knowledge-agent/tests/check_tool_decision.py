from app.services.tool_decision import decide_tool


def main() -> None:
    questions = [
        "你好",
        "这个文档主要讲了什么？",
        "我上传的资料里有没有提到 PDF 解析？",
    ]

    for question in questions:
        tool_name = decide_tool(question)
        print("-" * 40)
        print("问题:", question)
        print("模型选择:", tool_name)


if __name__ == "__main__":
    main()
