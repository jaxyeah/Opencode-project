"""Interactive debug utilities for ZPL macros."""

import logging
from pathlib import Path
from typing import Optional

from zpl_toolkit.connection import ZemaxConnection
from zpl_toolkit.executor import ZPLExecutor
from zpl_toolkit.parser import ZPLParser
from zpl_toolkit.types import ZPLError, ZPLExecutionResult

logger = logging.getLogger(__name__)


class ZPLDebugger:
    """Provides debugging and error-analysis tools for ZPL macros."""

    def __init__(
        self,
        connection: ZemaxConnection,
        executor: ZPLExecutor,
        parser: ZPLParser,
    ):
        self._conn = connection
        self._executor = executor
        self._parser = parser
        self._macro_text: Optional[list[str]] = None
        self._macro_path: Optional[str] = None

    def trace(self, macro_path: str) -> str:
        """Execute a macro and return full diagnostic output."""
        result = self._executor.run(macro_path)
        parsed = self._parser.parse(result)

        output: list[str] = [
            f"=== ZPL Trace: {Path(macro_path).name} ===",
            f"Exit code: {result.exit_code}",
            f"Execution time: {result.execution_time:.3f}s",
            "",
        ]

        if parsed.errors:
            output.append(f"Errors ({len(parsed.errors)}):")
            for err in parsed.errors:
                output.append(f"  {err}")
        else:
            output.append("No errors detected.")

        if result.stdout:
            output.extend(["", "--- STDOUT ---", result.stdout])

        if result.stderr:
            output.extend(["", "--- STDERR ---", result.stderr])

        output.append("=== End Trace ===")
        return "\n".join(output)

    def suggest_fix(self, error: ZPLError, macro_path: str) -> str:
        """Return a human-readable fix suggestion for a ZPL error."""
        context = self._read_error_context(macro_path, error.line_number)
        suggestions = self._match_suggestion(error)
        return f"{suggestions}\n\nContext (line {error.line_number}):\n{context}"

    def _read_error_context(
        self, macro_path: str, line_number: int, context_lines: int = 3
    ) -> str:
        """Read surrounding lines around an error."""
        try:
            with open(macro_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return "(unable to read macro file)"

        if line_number <= 0 or line_number > len(lines):
            return "(line number out of range)"

        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        result: list[str] = []
        for i in range(start, end):
            marker = ">>>" if i == line_number - 1 else "   "
            result.append(f"{marker} {i + 1:4d}: {lines[i].rstrip()}")

        return "\n".join(result)

    @staticmethod
    def _match_suggestion(error: ZPLError) -> str:
        """Match error to heuristic fix suggestions."""
        msg_lower = error.message.lower()

        if "undefined" in msg_lower:
            return (
                "Suggestion: The variable or function is not declared.\n"
                "  - Check for typos in the variable name.\n"
                "  - Ensure DECLARE or FOR/NEXT variables are properly scoped.\n"
                "  - If using a ZPL function, verify the function name is correct."
            )

        if "syntax" in msg_lower:
            return (
                "Suggestion: Syntax error detected.\n"
                "  - Check for missing ENDIF, NEXT, or parentheses.\n"
                "  - Verify that all FOR loops have NEXT, IF has ENDIF.\n"
                "  - Ensure quotes are properly closed."
            )

        if "type" in msg_lower:
            return (
                "Suggestion: Type mismatch.\n"
                "  - Check that numeric and string variables are not mixed.\n"
                "  - Use VAL() to convert strings to numbers and $STR() for numbers to strings."
            )

        if "file" in msg_lower or "not found" in msg_lower:
            return (
                "Suggestion: File not found.\n"
                "  - Verify the file path is correct.\n"
                "  - Use $FILEPATH() or put the file in the ZPL Macros directory.\n"
                "  - Check for missing file extension."
            )

        return (
            "Suggestion: Review the error line carefully.\n"
            "  - Check the ZPL reference in OpticStudio Help for the command at this line.\n"
            "  - Try running the macro line-by-line in the ZPL editor."
        )
