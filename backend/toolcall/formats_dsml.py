"""解析 Qwen/DeepSeek 原生 <|DSML|tool_calls> 格式的工具调用。
这种格式比 ##TOOL_CALL## 更能绕过 Qwen 的服务器端过滤。"""

from __future__ import annotations

import json
import re
from typing import Any


_DSML_PATTERN = re.compile(
    r"<\|DSML\|tool_calls>(.*?)</\|DSML\|tool_calls>",
    re.DOTALL | re.IGNORECASE,
)

_DSML_INVOKE_PATTERN = re.compile(
    r"<\|DSML\|invoke\s+name=\"(\S+)\">(.*?)</\|DSML\|invoke>",
    re.DOTALL | re.IGNORECASE,
)

_DSML_PARAM_PATTERN = re.compile(
    r"<\|DSML\|parameter\s+name=\"(\S+)\"><!\[CDATA\[(.*?)\]\]></\|DSML\|parameter>",
    re.DOTALL | re.IGNORECASE,
)


def parse_dsml_format(text: str, allowed_names: set[str]) -> list[dict[str, Any]]:
    """解析 <|DSML|tool_calls> 格式，返回标准化的工具调用列表。"""
    calls: list[dict[str, Any]] = []

    if not isinstance(text, str) or not text:
        return calls

    tc_match = _DSML_PATTERN.search(text)
    if not tc_match:
        return calls

    tc_block = tc_match.group(1)

    for invoke_match in _DSML_INVOKE_PATTERN.finditer(tc_block):
        tool_name = invoke_match.group(1).strip()
        invoke_content = invoke_match.group(2)

        params: dict[str, Any] = {}
        for param_match in _DSML_PARAM_PATTERN.finditer(invoke_content):
            param_name = param_match.group(1).strip()
            param_value = param_match.group(2)
            # 尝试解析 JSON 值
            try:
                parsed = json.loads(param_value)
            except (json.JSONDecodeError, TypeError, ValueError):
                parsed = param_value
            params[param_name] = parsed

        # 规范化工具名（不区分大小写匹配）
        normalized_name = tool_name
        name_lower = tool_name.lower()
        for allowed in allowed_names:
            if allowed.lower() == name_lower:
                normalized_name = allowed
                break

        calls.append({
            "name": normalized_name,
            "input": params,
        })

    return calls


def has_dsml_syntax(text: str) -> bool:
    """检测文本是否包含 <|DSML|tool_calls> 语法。"""
    if not text:
        return False
    return bool(_DSML_PATTERN.search(text))
