import re
from typing import Any

from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.schemas.tool import (
    CreateNoteInput,
    ListDocumentsInput,
    RetrieveDocumentsInput,
    SummarizeDocumentInput,
)
from app.services.tools import (
    create_note,
    list_documents,
    retrieve_documents,
    summarize_document,
)
from app.services.tool_registry import (
    ensure_tool_can_execute,
    ensure_tool_in_whitelist,
    get_session_tool_whitelist,
)
from app.services.input_guardrails import check_user_input, log_risk_input
from app.services.trace import TraceRecorder, elapsed_ms, now_ms, summarize_for_trace



class AgentService:
    """最小 Agent 主循环：判断工具、执行工具、返回回答。"""

    def __init__(
            self, 
            db: Session, 
            max_tool_calls: int = 5, 
            session_type: str = "default", #会话类型，决定默认的工具白名单
            allowed_tools: set[str] | None = None,#工具白名单
            trace_recorder: TraceRecorder | None = None,# trace 记录器

    ):
        self.db = db
        self.max_tool_calls = max_tool_calls
        self.session_type = session_type
        self.allowed_tools = (
            set(allowed_tools)
            if allowed_tools is not None
            else get_session_tool_whitelist(session_type)
        )
        self.trace_recorder = trace_recorder or TraceRecorder(db)


    def run(
            self, 
            user_message: str,
            confirmed_tool: str | None = None,
    ) -> dict[str, Any]:
        tool_calls = []
        current_message = user_message.strip()

        if not current_message:
            return {
                "answer": "问题不能为空。",
                "tool_calls": tool_calls,
            }
        
        #检查风险提示词
        guardrail_result = check_user_input(current_message)
        if not guardrail_result.allowed:
            risk_log = log_risk_input(self.db, current_message, guardrail_result)
            #风险信息
            input_guardrail = {
                "status": "blocked",
                "risk_level": guardrail_result.risk_level,
                "reasons": guardrail_result.reasons,
            }
            if risk_log is not None:
                input_guardrail["log_id"] = risk_log.id
            return {
                "answer": "这条输入包含明显的越权或提示词注入风险，我不能继续执行工具调用。",
                "tool_calls": tool_calls,
                "input_guardrail": input_guardrail,
            }


        for _ in range(self.max_tool_calls):
            tool_name, tool_input = self._decide_tool(current_message)

            if tool_name == "none":
                return {
                    "answer": "这个问题暂时不需要调用工具。",
                    "tool_calls": tool_calls,
                }

            try:
                tool_result = self._run_tool(tool_name, tool_input,confirmed=confirmed_tool == tool_name,)
            except PermissionError as exc:
                tool_call = {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "status": "permission_denied",
                    "error": str(exc),
                }
                tool_calls.append(tool_call)

                response = {
                    "answer": f"工具权限检查未通过：{exc}",
                    "tool_calls": tool_calls,
                }

                if "需要用户确认" in str(exc):
                    response["needs_confirmation"] = True
                    response["pending_tool"] = {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                    }

                return response   
            except ValidationError as exc:
                validation_log = {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "status": "validation_failed",
                    "error": str(exc),
                }
                tool_calls.append(validation_log)
                return {
                    "answer": f"工具参数校验失败：{exc}",
                    "tool_calls": tool_calls,
                }
            except Exception as exc:
                tool_calls.append(
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                return {
                    "answer": f"工具调用失败：{exc}",
                    "tool_calls": tool_calls,
                }

            tool_calls.append(
                {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "tool_result": tool_result,
                    "status": "success",
                }
            )

            return {
                "answer": self._build_answer(tool_name, tool_result),
                "tool_calls": tool_calls,
            }

        return {
            "answer": f"工具调用次数超过限制：{self.max_tool_calls}",
            "tool_calls": tool_calls,
        }

    def _decide_tool(self, user_message: str) -> tuple[str, dict[str, Any]]:
        """匹配关键词来确定调用什么工具"""
        if "哪些文档" in user_message or "文档列表" in user_message:
            return "list_documents", {}

        if "总结" in user_message and "文档" in user_message:
            document_id = self._extract_first_number(user_message)
            if document_id is None:
                return "summarize_document", {"document_id": None}
            return "summarize_document", {"document_id": document_id}

        if "文档" in user_message or "资料" in user_message or "知识库" in user_message:
            return "retrieve_documents", {"query": user_message, "limit": 3}

        return "none", {}

    def _run_tool(
            self, 
            tool_name: str, 
            tool_input: dict[str, Any], #传给工具的参数字典
            confirmed: bool = False,    #是否已获得用户确认（默认 False）
    ) -> Any:
        """根据工具名和参数来调用工具，并记录工具 trace。"""
        start_ms = now_ms()

        try:
            ensure_tool_in_whitelist(tool_name, self.allowed_tools)
            ensure_tool_can_execute(tool_name, confirmed=confirmed)

            if tool_name == "list_documents":
                ListDocumentsInput.model_validate(tool_input)
                result = list_documents(self.db)

            elif tool_name == "retrieve_documents":
                validated_input = RetrieveDocumentsInput.model_validate(tool_input)
                result = retrieve_documents(
                    self.db,
                    query=validated_input.query,
                    limit=validated_input.limit,
                )

            elif tool_name == "summarize_document":
                validated_input = SummarizeDocumentInput.model_validate(tool_input)
                result = summarize_document(
                    self.db,
                    document_id=validated_input.document_id,
                )

            elif tool_name == "create_note":
                validated_input = CreateNoteInput.model_validate(tool_input)
                result = create_note(
                    self.db,
                    title=validated_input.title,
                    content=validated_input.content,
                    source_ids=validated_input.source_ids,
                )

            else:
                raise ValueError(f"未知工具：{tool_name}")

            self._record_tool_trace(
                tool_name=tool_name,
                tool_input=tool_input,
                output_data=summarize_for_trace(result),
                latency_ms=elapsed_ms(start_ms),
                status="success",
            )
            return result

        except PermissionError as exc:
            self._record_tool_trace(
                tool_name=tool_name,
                tool_input=tool_input,
                output_data={"error": str(exc)},
                latency_ms=elapsed_ms(start_ms),
                status="blocked",
            )
            raise

        except Exception as exc:
            self._record_tool_trace(
                tool_name=tool_name,
                tool_input=tool_input,
                output_data={"error": str(exc)},
                latency_ms=elapsed_ms(start_ms),
                status="failed",
            )
            raise

    def _record_tool_trace(
        self,
        *,
        tool_name: str,
        tool_input: dict[str, Any],
        output_data: dict | None,
        latency_ms: float,
        status: str,
    ) -> None:
        """把一次工具调用写入 trace。"""

        self.trace_recorder.record(
            tool_name=tool_name,
            input_data={
                "type": "tool_call",
                "tool_name": tool_name,
                "arguments": tool_input,
            },
            output_data=output_data,
            latency_ms=latency_ms,
            status=status,
        )
        

    def _build_answer(self, tool_name: str, tool_result: Any) -> str:
        if tool_name == "list_documents":
            if not tool_result:
                return "你还没有上传任何文档。"

            lines = ["你已经上传了这些文档："]
            for document in tool_result:
                lines.append(
                    f'- #{document["document_id"]} {document["filename"]}，'
                    f'{document["page_count"]} 页'
                )
            return "\n".join(lines)

        if tool_name == "retrieve_documents":
            if not tool_result:
                return "我在知识库里没有检索到相关片段。"

            lines = ["我检索到了这些相关片段："]
            for item in tool_result:
                lines.append(
                    f'- chunk #{item["chunk_id"]}，第 {item["page_number"]} 页，'
                    f'distance={item["distance"]:.4f}'
                )
            return "\n".join(lines)

        if tool_name == "summarize_document":
            return str(tool_result["summary"])

        return str(tool_result)

    def _extract_first_number(self, text: str) -> int | None:
        match = re.search(r"\d+", text)
        if match is None:
            return None
        return int(match.group())
