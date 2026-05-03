from .agent import ReActAgent
from .models import ScriptedReasoningModel
from .tools import ToolRegistry, calculator_tool, knowledge_base_tool


def main() -> None:
    agent = ReActAgent(
        model=ScriptedReasoningModel(),
        tools=ToolRegistry([calculator_tool(), knowledge_base_tool()]),
    )
    result = agent.run("Calculate 42 * 7")
    print(result.answer)
    print(result.trace.as_dict())


if __name__ == "__main__":
    main()

