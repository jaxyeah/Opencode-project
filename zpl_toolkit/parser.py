"""ZPL output parser and error extractor."""

import re
from typing import Any

from zpl_toolkit.types import ZPLError, ZPLExecutionResult, ZPLParseResult


class ZPLParser:
    """Parses ZPL execution output to extract structured errors and data."""

    # Common ZPL error patterns
    _ERROR_PATTERNS = [
        # "Error at line N: message" or "ERROR at line N: message"
        re.compile(
            r"^\s*(?:Error|ERROR)\s+at\s+line\s+(\d+)\s*:\s*(.+)$",
            re.IGNORECASE,
        ),
        # "*** Error at line N: message"
        re.compile(
            r"^\*{3}\s+Error\s+at\s+line\s+(\d+)\s*:\s*(.+)$",
            re.IGNORECASE,
        ),
        # "Syntax error: message / line N"
        re.compile(
            r"^Syntax\s+error\s*:\s*(.+?)\s*/\s*line\s+(\d+)\s*$",
            re.IGNORECASE,
        ),
        # "Undefined variable: VARNAME"
        re.compile(
            r"^Undefined\s+(?:variable|function)\s*:\s*(.+)$",
            re.IGNORECASE,
        ),
        # "Warning: ..."
        re.compile(
            r"^\s*(?:Warning|WARNING)\s*:\s*(.+)$",
            re.IGNORECASE,
        ),
    ]

    def parse(self, result: ZPLExecutionResult) -> ZPLParseResult:
        """Parse execution result into structured output."""
        errors = self.extract_errors(result.stderr)
        data = self.extract_data(result.stdout)
        return ZPLParseResult(
            errors=errors,
            raw_output=f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}",
            data=data,
        )

    def extract_errors(self, stderr: str) -> list[ZPLError]:
        """Extract structured errors from ZPL stderr text."""
        if not stderr or not stderr.strip():
            return []

        # Normalize encoding
        try:
            text = stderr.encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            text = stderr

        errors: list[ZPLError] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            err = self._match_line(line)
            if err is not None:
                errors.append(err)
            elif self._looks_like_error(line):
                errors.append(
                    ZPLError(
                        line_number=0,
                        error_code="E_UNKNOWN",
                        message=line[:200],
                        severity="ERROR",
                    )
                )

        return errors

    def _match_line(self, line: str) -> ZPLError | None:
        """Try to match a line against known error patterns."""
        for pattern in self._ERROR_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue

            groups = match.groups()
            if len(groups) == 2:
                # Pattern with line number + message
                line_num = int(groups[0])
                message = groups[1].strip()
                return ZPLError(
                    line_number=line_num,
                    error_code=self._classify_error(message),
                    message=message,
                    severity="WARNING" if "warning" in line.lower() else "ERROR",
                )
            elif len(groups) == 1:
                # Pattern with message only
                message = groups[0].strip()
                return ZPLError(
                    line_number=0,
                    error_code=self._classify_error(message),
                    message=message,
                    severity="WARNING" if "warning" in line.lower() else "ERROR",
                )
        return None

    @staticmethod
    def _looks_like_error(line: str) -> bool:
        """Heuristic: does this line look like an error even if pattern doesn't match?"""
        error_markers = [
            "error",
            "cannot",
            "failed",
            "invalid",
            "unexpected",
            "not found",
            "access denied",
        ]
        lower = line.lower()
        return any(marker in lower for marker in error_markers)

    @staticmethod
    def _classify_error(message: str) -> str:
        """Heuristically classify the error type from message text."""
        msg_lower = message.lower()
        if "undefined" in msg_lower:
            return "E_UNDEFINED"
        if "syntax" in msg_lower:
            return "E_SYNTAX"
        if "type" in msg_lower:
            return "E_TYPE"
        if "overflow" in msg_lower or "divide by zero" in msg_lower:
            return "E_MATH"
        if "memory" in msg_lower:
            return "E_MEMORY"
        if "file" in msg_lower or "not found" in msg_lower:
            return "E_FILE"
        return "E_GENERAL"

    def extract_data(self, stdout: str) -> dict[str, Any]:
        """Extract structured data from ZPL stdout.

        Parses PRINT statements that output KEY=VALUE or tabular data.
        """
        if not stdout or not stdout.strip():
            return {}

        data: dict[str, Any] = {}
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            # KEY=VALUE pattern
            if "=" in line and not line.startswith(("!", "#", "*")):
                parts = line.split("=", 1)
                key = parts[0].strip()
                value = parts[1].strip()
                # Try numeric conversion
                try:
                    data[key] = float(value)
                except ValueError:
                    data[key] = value

        return data
