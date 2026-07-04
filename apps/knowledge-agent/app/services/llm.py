import time
from openai import OpenAI
from app.core.config import settings
from app.services.trace import TraceRecorder, elapsed_ms, now_ms, preview_text

class LLMService:
    """LLM 服务，负责调用大模型生成普通回答或流式回答。"""

    def __init__(self, trace_recorder: TraceRecorder | None = None):
        """初始化兼容 OpenAI 协议的 DeepSeek 客户端。"""
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
        self.trace_recorder = trace_recorder


    def chat(self, prompt: str, model: str = "deepseek-v4-pro") -> tuple[str, float]:
        """一次性调用大模型，返回完整回答和调用耗时。"""

        start_ms = now_ms()

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = elapsed_ms(start_ms)
            latency = latency_ms / 1000
            answer = response.choices[0].message.content or ""

            # prompt_tokens输入token数、completion_tokens输出token数、total_tokens总token数
            usage = getattr(response, "usage", None)#getattr(对象, 属性名, 默认值)
            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            if self.trace_recorder is not None:
                self.trace_recorder.record(#数据交给它填表
                    tool_name=None,
                    input_data={
                        "type": "llm_call",
                        "model": model,
                        "prompt_preview": preview_text(prompt),
                    },
                    output_data={
                        "answer_preview": preview_text(answer),
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    },
                    latency_ms=latency_ms,
                    status="success",
                )

            return answer, latency

        except Exception as exc:
            latency_ms = elapsed_ms(start_ms)

            if self.trace_recorder is not None:
                self.trace_recorder.record(
                    tool_name=None,
                    input_data={
                        "type": "llm_call",
                        "model": model,
                        "prompt_preview": preview_text(prompt),#预览内容
                    },
                    output_data={
                        "error": str(exc),
                    },
                    latency_ms=latency_ms,
                    status="failed",
                )
            raise


    def stream_chat(self, prompt: str, model: str = "deepseek-v4-pro"):
        """流式调用大模型，每次 yield 一小段回答文本。"""
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
