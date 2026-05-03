from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


ToolHandler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: ToolHandler
    required_keys: tuple[str, ...] = ()

    def invoke(self, arguments: dict[str, Any]) -> str:
        missing = [key for key in self.required_keys if key not in arguments]
        if missing:
            raise ValueError(f"Tool '{self.name}' missing arguments: {', '.join(missing)}")
        return self.handler(arguments)


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def descriptions(self) -> list[dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]


def calculator_tool() -> Tool:
    def handle(arguments: dict[str, Any]) -> str:
        expression = str(arguments["expression"])
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            raise ValueError("Calculator expression contains unsupported characters")
        return str(eval(expression, {"__builtins__": {}}, {}))

    return Tool(
        name="calculator",
        description="Safely evaluates basic arithmetic expressions.",
        handler=handle,
        required_keys=("expression",),
    )


def knowledge_base_tool() -> Tool:
    facts = {
        "react": "ReAct alternates reasoning steps with tool actions and observations.",
        "reflection": "Reflection adds critique and revision before final output.",
        "plan_execute": "Plan and Execute separates task decomposition from execution.",
    }

    def handle(arguments: dict[str, Any]) -> str:
        query = str(arguments["query"]).lower()
        return facts.get(query, "No matching fact found.")

    return Tool(
        name="knowledge_base",
        description="Looks up known agent architecture facts by key.",
        handler=handle,
        required_keys=("query",),
    )

