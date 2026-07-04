from dataclasses import dataclass
from enum import Enum


class ToolPermission(str, Enum):
    """Agent 工具权限等级。"""

    READ_ONLY = "read_only"
    WRITE = "write"
    DANGEROUS = "dangerous"


@dataclass(frozen=True)
class ToolDefinition:
    """单个 Agent 工具的权限定义。"""

    name: str
    permission: ToolPermission
    description: str
    enabled: bool = True


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "list_documents": ToolDefinition(
        name="list_documents",
        permission=ToolPermission.READ_ONLY,
        description="查询已上传文档列表，不修改数据库。",
    ),
    "retrieve_documents": ToolDefinition(
        name="retrieve_documents",
        permission=ToolPermission.READ_ONLY,
        description="根据用户问题检索相关文档片段，不修改数据库。",
    ),
    "summarize_document": ToolDefinition(
        name="summarize_document",
        permission=ToolPermission.READ_ONLY,
        description="总结指定文档并返回引用来源，不修改数据库。",
    ),
    "create_note": ToolDefinition(
        name="create_note",
        permission=ToolPermission.WRITE,
        description="创建笔记，会写入数据库。",
    ),
    "delete_document": ToolDefinition(
        name="delete_document",
        permission=ToolPermission.DANGEROUS,
        description="删除文档数据，当前不开放给 Agent。",
        enabled=False,
    ),
}

SESSION_TOOL_WHITELISTS: dict[str, frozenset[str]] = {
    "default": frozenset(
        {
            "list_documents",
            "retrieve_documents",
            "summarize_document",
        }
    ),
    "note": frozenset(
        {
            "list_documents",
            "retrieve_documents",
            "summarize_document",
            "create_note",
        }
    ),
}



def get_tool_definition(tool_name: str) -> ToolDefinition:
    """根据工具名读取权限定义。"""

    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"未知工具：{tool_name}")

    return TOOL_REGISTRY[tool_name]


def can_execute_directly(tool_name: str) -> bool:
    """判断工具是否允许 Agent 直接执行。"""

    tool = get_tool_definition(tool_name)
    return tool.enabled and tool.permission == ToolPermission.READ_ONLY

def requires_confirmation(tool_name: str) -> bool:
    """判断工具是否需要用户确认。"""

    tool = get_tool_definition(tool_name)
    return tool.enabled and tool.permission == ToolPermission.WRITE

def get_session_tool_whitelist(session_type: str = "default") -> set[str]:
    """根据会话类型返回允许使用的工具白名单。"""

    if session_type not in SESSION_TOOL_WHITELISTS:
        raise ValueError(f"未知会话类型：{session_type}")

    return set(SESSION_TOOL_WHITELISTS[session_type])


def ensure_tool_in_whitelist(
    tool_name: str,
    allowed_tools: set[str],
) -> None:
    """检查工具是否在当前会话白名单中。"""

    get_tool_definition(tool_name)

    if tool_name not in allowed_tools:
        raise PermissionError(f"工具 {tool_name} 不在当前会话白名单中，不能执行。")


def ensure_tool_can_execute(
    tool_name: str,
    confirmed: bool = False,
) -> None:
    """检查工具是否允许执行。"""

    tool = get_tool_definition(tool_name)

    if not tool.enabled:
        raise PermissionError(f"工具 {tool_name} 当前未开放给 Agent 使用。")

    if tool.permission == ToolPermission.DANGEROUS:
        raise PermissionError(f"工具 {tool_name} 是危险工具，当前不允许 Agent 执行。")

    if tool.permission == ToolPermission.WRITE and not confirmed:
        raise PermissionError(f"工具 {tool_name} 是写入工具，需要用户确认后才能执行。")


def ensure_tool_can_execute_directly(tool_name: str) -> None:
    """只允许不需要确认的工具直接执行。"""

    ensure_tool_can_execute(tool_name, confirmed=False)



def list_tool_permissions() -> list[dict]:
    """返回工具权限表，方便测试、文档或接口展示。"""

    return [
        {
            "name": tool.name,
            "permission": tool.permission.value,
            "description": tool.description,
            "enabled": tool.enabled,
            "can_execute_directly": can_execute_directly(tool.name),
            "requires_confirmation": requires_confirmation(tool.name),
        }
        for tool in TOOL_REGISTRY.values()
    ]
