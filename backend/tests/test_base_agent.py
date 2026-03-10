from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent


class _FakeAgent(BaseAgent):
    def _get_system_prompt(self) -> str:
        return "system"

    def _get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "toolSpec": {
                    "name": "echo_tool",
                    "description": "Echo input back.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {"value": {"type": "string"}},
                            "required": ["value"],
                        }
                    },
                }
            }
        ]

    def _execute_tool(self, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        assert name == "echo_tool"
        return {
            "echo": input_data["value"],
            "sql": "SELECT 1",
            "row_count": 2,
            "rows": [{"value": input_data["value"]}],
        }


def test_base_agent_runs_tool_loop_and_collects_trace(monkeypatch) -> None:
    responses = [
        {
            "stopReason": "tool_use",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tool-1",
                                "name": "echo_tool",
                                "input": {"value": "apple"},
                            }
                        }
                    ],
                }
            },
        },
        {
            "stopReason": "end_turn",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Final answer from tools."}],
                }
            },
        },
    ]

    def fake_converse_with_tools(**kwargs):
        _ = kwargs
        return responses.pop(0)

    monkeypatch.setattr(
        "backend.app.agents.base.converse_with_tools",
        fake_converse_with_tools,
    )

    result = _FakeAgent().run("Test question")

    assert result.answer == "Final answer from tools."
    assert result.sql_used == "SELECT 1"
    assert result.rows_found == 2
    assert result.tool_trace == [
        {
            "tool": "echo_tool",
            "status": "success",
            "input": {"value": "apple"},
            "output_preview": {
                "sql": "SELECT 1",
                "row_count": 2,
                "sample_rows": [{"value": "apple"}],
                "echo": "apple",
            },
        }
    ]
