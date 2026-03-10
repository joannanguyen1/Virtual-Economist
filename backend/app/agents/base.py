"""Base tool-use agent shared by HousingAgent and MarketAgent."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from loguru import logger

from backend.app.services.bedrock import CLAUDE_SONNET, converse_with_tools


@dataclass
class AgentResult:
    """Structured output from any agent run."""

    answer: str
    sql_used: str | None = None
    rows_found: int = 0
    error: str | None = None
    tool_trace: list[dict[str, Any]] | None = None


class BaseAgent(ABC):
    """Reusable Bedrock tool-use loop with small hooks per domain."""

    def run(self, question: str) -> AgentResult:
        """Run a Bedrock tool-use loop until the model returns a final answer."""
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": question}]},
        ]
        tool_trace: list[dict[str, Any]] = []
        sql_statements: list[str] = []
        total_rows = 0

        try:
            for _ in range(self._max_rounds()):
                response = converse_with_tools(
                    messages=messages,
                    tools=self._get_tools(),
                    system=self._get_system_prompt(),
                    model_id=self._model_id(),
                    max_tokens=self._max_tokens(),
                    temperature=0.0,
                )
                message = response["output"]["message"]
                stop_reason = response.get("stopReason")
                messages.append(message)

                if stop_reason == "tool_use":
                    tool_results: list[dict[str, Any]] = []
                    tool_uses = [
                        block["toolUse"]
                        for block in message.get("content", [])
                        if "toolUse" in block
                    ]
                    if not tool_uses:
                        raise RuntimeError("Bedrock requested tool use without any tool blocks.")

                    for tool_use in tool_uses:
                        name = str(tool_use.get("name", ""))
                        tool_input = tool_use.get("input") or {}
                        tool_use_id = str(tool_use.get("toolUseId", ""))

                        try:
                            output = self._execute_tool(name, tool_input)
                            sql = self._extract_sql(output)
                            if sql:
                                sql_statements.append(sql)
                            total_rows += self._extract_row_count(output)

                            tool_trace.append(
                                {
                                    "tool": name,
                                    "status": "success",
                                    "input": tool_input,
                                    "output_preview": self._preview_tool_output(output),
                                }
                            )
                            tool_results.append(
                                {
                                    "toolResult": {
                                        "toolUseId": tool_use_id,
                                        "content": [{"json": self._tool_result_payload(output)}],
                                        "status": "success",
                                    }
                                }
                            )
                        except Exception as exc:
                            logger.warning(
                                "{} tool failed | tool={} | error={}",
                                self.__class__.__name__,
                                name,
                                exc,
                            )
                            tool_trace.append(
                                {
                                    "tool": name,
                                    "status": "error",
                                    "input": tool_input,
                                    "error": str(exc),
                                }
                            )
                            tool_results.append(
                                {
                                    "toolResult": {
                                        "toolUseId": tool_use_id,
                                        "content": [{"json": {"error": str(exc)}}],
                                        "status": "error",
                                    }
                                }
                            )

                    messages.append({"role": "user", "content": tool_results})
                    continue

                answer = self._extract_text(message)
                if answer:
                    return AgentResult(
                        answer=answer,
                        sql_used="\n\n".join(sql_statements) or None,
                        rows_found=total_rows,
                        tool_trace=tool_trace or None,
                    )

                raise RuntimeError(f"Bedrock returned stopReason={stop_reason!r} without text.")

            raise RuntimeError("Agent reached the tool-use round limit without a final answer.")

        except Exception as exc:
            logger.exception("{} error | question={!r}", self.__class__.__name__, question)
            return AgentResult(
                answer=self._error_answer(),
                sql_used="\n\n".join(sql_statements) or None,
                rows_found=total_rows,
                error=str(exc),
                tool_trace=tool_trace or None,
            )

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt for the agent."""

    @abstractmethod
    def _get_tools(self) -> list[dict[str, Any]]:
        """Return Bedrock tool definitions for the agent."""

    @abstractmethod
    def _execute_tool(self, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute one tool call and return a JSON-serializable result."""

    def _error_answer(self) -> str:
        """Default user-facing fallback when the tool loop fails."""
        return (
            "I'm sorry, I ran into an issue while gathering data for that question. "
            "Please try rephrasing it or try again in a moment."
        )

    def _model_id(self) -> str:
        return CLAUDE_SONNET

    def _max_rounds(self) -> int:
        return 6

    def _max_tokens(self) -> int:
        return 2048

    def _extract_text(self, message: dict[str, Any]) -> str:
        """Join any text blocks from a Bedrock assistant message."""
        parts = [
            block["text"].strip()
            for block in message.get("content", [])
            if isinstance(block, dict) and block.get("text")
        ]
        text = "\n".join(part for part in parts if part).strip()
        return re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()

    def _tool_result_payload(self, output: Any) -> Any:
        """Ensure the Bedrock toolResult payload is JSON-like."""
        return self._json_safe(output)

    def _preview_tool_output(self, output: Any) -> Any:
        """Small debug preview returned in the API's tool trace."""
        if not isinstance(output, dict):
            return output

        preview: dict[str, Any] = {}
        if output.get("sql"):
            preview["sql"] = output["sql"]
        if output.get("row_count") is not None:
            preview["row_count"] = output["row_count"]
        if output.get("columns"):
            preview["columns"] = output["columns"]
        if isinstance(output.get("rows"), list):
            rows = output["rows"]
            preview["sample_rows"] = rows[:2]
        scalar_items = {
            key: value
            for key, value in output.items()
            if key not in {"sql", "row_count", "columns", "rows"}
            and isinstance(value, str | int | float | bool)
        }
        for key, value in list(scalar_items.items())[:6]:
            preview[key] = value
        return self._json_safe(preview or output)

    def _extract_sql(self, output: Any) -> str | None:
        if isinstance(output, dict):
            sql = output.get("sql") or output.get("sql_used")
            return str(sql) if sql else None
        return None

    def _extract_row_count(self, output: Any) -> int:
        if not isinstance(output, dict):
            return 0
        row_count = output.get("row_count", output.get("rows_found", 0))
        try:
            return int(row_count or 0)
        except (TypeError, ValueError):
            return 0

    def _json_safe(self, value: Any) -> Any:
        """Recursively coerce common Python/DB types into Bedrock document types."""
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime | date):
            return value.isoformat()
        if isinstance(value, str | int | float | bool) or value is None:
            return value
        return str(value)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _clean_sql(self, raw: str) -> str:
        """Strip markdown code fences that the LLM sometimes wraps around SQL."""
        cleaned = raw.strip()
        if cleaned.startswith("```sql"):
            cleaned = cleaned[6:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _safe_execute(
        self,
        sql: str,
        cursor,
        params: tuple[Any, ...] | None = None,
    ) -> tuple[list[tuple], list[str]]:  # type: ignore[no-untyped-def]
        """Execute a SELECT-only query and return (rows, column_names)."""
        normalized = sql.strip().upper()
        if not normalized.startswith("SELECT"):
            raise ValueError(
                f"Safety check failed: only SELECT queries are allowed. Got: {sql[:80]!r}"
            )
        cursor.execute(sql, params)
        rows: list[tuple] = cursor.fetchall()
        columns: list[str] = [desc[0] for desc in cursor.description] if cursor.description else []
        return rows, columns
