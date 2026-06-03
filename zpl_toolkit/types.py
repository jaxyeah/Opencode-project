"""Data models for ZPL execution, parsing, and generation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ConnectionConfig:
    """Configuration for OpticStudio ZOS-API connection."""

    opticstudio_path: Optional[str] = None
    """Explicit path to OpticStudio installation. Auto-detected if None."""

    headless: bool = True
    """Run OpticStudio without GUI. Default: True for batch/CLI operation."""

    timeout: int = 60
    """Connection timeout in seconds."""

    def __str__(self) -> str:
        return (
            f"ConnectionConfig(path={self.opticstudio_path or 'auto'}, "
            f"headless={self.headless}, timeout={self.timeout}s)"
        )


@dataclass
class ZPLExecutionResult:
    """Result of executing a single ZPL macro."""

    exit_code: int
    """Exit code from ZPL execution. 0 = success."""

    stdout: str
    """Standard output captured from ZPL execution."""

    stderr: str
    """Standard error captured from ZPL execution."""

    execution_time: float
    """Execution time in seconds."""

    macro_path: str
    """Path to the executed ZPL macro file."""

    def __str__(self) -> str:
        status = "OK" if self.exit_code == 0 else f"FAIL({self.exit_code})"
        lines = len(self.stdout.splitlines()) if self.stdout else 0
        return (
            f"ZPLExecution({status}) [{self.macro_path}] "
            f"time={self.execution_time:.2f}s out={lines}L"
        )


@dataclass
class ZPLError:
    """A single error from ZPL execution."""

    line_number: int
    """1-based line number where the error occurred. 0 if unknown."""

    error_code: str
    """Error code string (e.g., 'E_UNDEFINED', 'E_SYNTAX')."""

    message: str
    """Human-readable error message."""

    severity: str
    """Severity level: 'ERROR' or 'WARNING'."""

    def __str__(self) -> str:
        loc = f"L{self.line_number}" if self.line_number > 0 else "??"
        return f"[{self.severity}] {loc}: {self.message}"


@dataclass
class ZPLParseResult:
    """Parsed output from a ZPL macro execution."""

    errors: list[ZPLError] = field(default_factory=list)
    """List of errors extracted from stderr."""

    raw_output: str = ""
    """Raw unparsed output for debugging."""

    data: dict = field(default_factory=dict)
    """Structured data extracted from stdout PRINT/VECTOR output."""

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def __str__(self) -> str:
        if not self.errors:
            return "ZPLParse(clean)"
        return "\n".join(str(e) for e in self.errors)


@dataclass
class MacroInfo:
    """Metadata about a ZPL macro file."""

    path: str
    """Full filesystem path to the macro."""

    name: str
    """Filename without path."""

    size: int
    """File size in bytes."""

    last_modified: datetime
    """Last modification timestamp."""

    category: str = "general"
    """Detected category (tilt_analysis, distortion, wedge_analysis, etc.)."""

    line_count: int = 0
    """Number of lines in the macro file."""

    header_comments: list[str] = field(default_factory=list)
    """First N comment lines (ZPL comments start with ! or #)."""

    def __str__(self) -> str:
        return (
            f"Macro({self.category}) {self.name} "
            f"[{self.line_count}L, {self.size}B, {self.last_modified:%Y-%m-%d}]"
        )


@dataclass
class RegressionTestResult:
    """Result of a single regression test comparison."""

    macro_path: str
    """Path to the macro that was tested."""

    passed: bool
    """True if actual output matches expected baseline."""

    expected_output: str
    """Expected output from baseline file."""

    actual_output: str
    """Actual output from this execution."""

    diff: str = ""
    """Human-readable diff between expected and actual (empty if passed)."""

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        diff_note = f" diff={len(self.diff)}chars" if self.diff else ""
        return f"Regression({status}) {self.macro_path}{diff_note}"


@dataclass
class GenerationTemplate:
    """A ZPL code generation template."""

    name: str
    """Template identifier (e.g., 'tilt-analysis', 'mtf-analysis')."""

    description: str
    """Human-readable description of what this template generates."""

    parameters: dict
    """Required parameters: {name: default_value_or_None}."""

    template_body: str
    """Template body with {param_name} placeholders."""

    def __str__(self) -> str:
        params = ", ".join(self.parameters.keys())
        return f"Template({self.name}): {self.description} [params: {params}]"
