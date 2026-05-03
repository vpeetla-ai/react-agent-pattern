from react_agent_pattern import (
    ReActAgent,
    ScriptedReasoningModel,
    ToolRegistry,
    calculator_tool,
    knowledge_base_tool,
)


def build_agent() -> ReActAgent:
    return ReActAgent(
        model=ScriptedReasoningModel(),
        tools=ToolRegistry([calculator_tool(), knowledge_base_tool()]),
    )


def test_react_agent_uses_tool_then_finalizes() -> None:
    result = build_agent().run("Calculate 2 + 3 * 4")

    assert result.answer == "Grounded answer: 14"
    assert result.observations == ["14"]
    assert [event.name for event in result.trace.events].count("tool.observation") == 1


def test_react_agent_answers_architecture_lookup() -> None:
    result = build_agent().run("What is ReAct?")

    assert "alternates reasoning" in result.answer

