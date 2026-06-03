"""ZPL macro execution engine for ZOS-API."""

import logging
import time
from pathlib import Path

from zpl_toolkit.connection import ZemaxConnection
from zpl_toolkit.types import ZPLExecutionResult

logger = logging.getLogger(__name__)


class ZPLExecutor:
    """Executes ZPL macros in OpticStudio via ZOS-API.

    ZOS-API does not have a direct public "run ZPL" endpoint. This
    executor uses RunCommand (the internal command interface) which
    dispatches ZPL execution to the underlying OpticStudio engine.

    PRINT output from ZPL is routed to the OpticStudio output window
    and is not directly retrievable via ZOS-API.  For output capture,
    wrap the ZPL to write results to a file instead of PRINT.
    """

    def __init__(self, connection: ZemaxConnection):
        if not connection.is_connected:
            raise RuntimeError(
                "ZemaxConnection must be connected before creating ZPLExecutor"
            )
        self._conn = connection

    def run(self, macro_path: str, timeout: int = 120) -> ZPLExecutionResult:
        """Execute a ZPL macro.

        Args:
            macro_path: Path to the .ZPL file.
            timeout: Maximum execution time in seconds (best-effort).

        Returns:
            ZPLExecutionResult with exit code and available output.

        Raises:
            FileNotFoundError: Macro file does not exist.
        """
        macro_file = Path(macro_path)
        if not macro_file.exists():
            raise FileNotFoundError(f"Macro not found: {macro_path}")

        if not macro_file.suffix.lower() == ".zpl":
            logger.warning("Macro has non-standard extension: %s", macro_file.suffix)

        abs_path = str(macro_file.resolve())
        logger.info("Executing: %s", abs_path)
        start = time.perf_counter()

        try:
            exit_code, stdout, stderr = self._execute(abs_path)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error("Execution failed: %s", exc)
            return ZPLExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                execution_time=elapsed,
                macro_path=abs_path,
            )

        elapsed = time.perf_counter() - start
        status = "OK" if exit_code == 0 else f"FAIL({exit_code})"
        logger.info("Execution %s in %.2fs", status, elapsed)

        return ZPLExecutionResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            execution_time=elapsed,
            macro_path=abs_path,
        )

    def run_batch(
        self, macro_paths: list[str], timeout: int = 120
    ) -> list[ZPLExecutionResult]:
        """Execute multiple ZPL macros sequentially."""
        results: list[ZPLExecutionResult] = []
        for i, path in enumerate(macro_paths, 1):
            logger.info("Batch [%d/%d]: %s", i, len(macro_paths), path)
            results.append(self.run(path, timeout=timeout))
        return results

    # ── internals ────────────────────────────────────────────────

    def _execute(self, macro_path: str) -> tuple[int, str, str]:
        """Run a ZPL macro via ZOS-API RunCommand and capture what we can."""
        app = self._conn.application

        stdout: list[str] = []
        stderr: list[str] = []
        exit_code = 0

        # Enable message logging to capture any OpticStudio output
        try:
            app.BeginMessageLogging()
        except Exception:
            logger.debug("BeginMessageLogging unavailable")

        try:
            _ = app.RunCommand(f'RUNMACRO "{macro_path}"')
        except Exception as exc:
            stderr.append(f"RunCommand error: {exc}")
            exit_code = 1
        finally:
            # Retrieve whatever OpticStudio logged
            try:
                msgs = app.RetrieveLogMessages()
                if msgs:
                    stdout.extend(str(m) for m in msgs)
            except Exception:
                pass
            try:
                app.EndMessageLogging()
            except Exception:
                pass

        return exit_code, "\n".join(stdout).strip(), "\n".join(stderr).strip()
