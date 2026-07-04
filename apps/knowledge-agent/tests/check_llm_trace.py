from app.services.llm import LLMService
from app.services.trace import TraceRecorder, preview_text


class FakeMessage:
    content = "这是模拟模型回答。"


class FakeChoice:
    message = FakeMessage()


class FakeUsage:
    prompt_tokens = 10
    completion_tokens = 5
    total_tokens = 15


class FakeResponse:
    choices = [FakeChoice()]
    usage = FakeUsage()


class FakeCompletions:
    def create(self, **kwargs):
        return FakeResponse()


class FakeChat:
    completions = FakeCompletions()


class FakeClient:
    chat = FakeChat()


class MemoryTraceRecorder(TraceRecorder):
    def __init__(self):
        super().__init__(db=None)
        self.records = []

    def record(
        self,
        *,
        tool_name,
        input_data,
        output_data,
        latency_ms,
        status,
    ):
        self.records.append(
            {
                "tool_name": tool_name,
                "input_data": input_data,
                "output_data": output_data,
                "latency_ms": latency_ms,
                "status": status,
            }
        )
        return None


def main() -> None:
    assert preview_text("abc") == "abc"
    assert preview_text("a" * 300).endswith("...")

    recorder = MemoryTraceRecorder()
    llm = LLMService(trace_recorder=recorder)
    llm.client = FakeClient()

    answer, latency = llm.chat("请回答一个测试问题", model="fake-model")

    assert answer == "这是模拟模型回答。"
    assert latency >= 0
    assert len(recorder.records) == 1

    record = recorder.records[0]
    assert record["tool_name"] is None
    assert record["status"] == "success"
    assert record["input_data"]["type"] == "llm_call"
    assert record["input_data"]["model"] == "fake-model"
    assert record["output_data"]["answer_preview"] == "这是模拟模型回答。"
    assert record["output_data"]["prompt_tokens"] == 10
    assert record["output_data"]["completion_tokens"] == 5
    assert record["output_data"]["total_tokens"] == 15

    print("模型调用 trace 记录:", record)
    print("Day 51 模型调用 Trace 检查通过。")


if __name__ == "__main__":
    main()
