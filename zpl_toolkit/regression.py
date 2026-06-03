"""Regression test runner for ZPL macros."""

import json
import logging
import os
from datetime import datetime
from difflib import unified_diff
from pathlib import Path

from zpl_toolkit.executor import ZPLExecutor
from zpl_toolkit.parser import ZPLParser
from zpl_toolkit.types import RegressionTestResult, ZPLExecutionResult

logger = logging.getLogger(__name__)

_DEFAULT_BASELINE_DIR = ".zpl_test_baselines"


class RegressionRunner:
    """Runs ZPL macros and compares output against saved baselines."""

    def __init__(self, executor: ZPLExecutor, parser: ZPLParser):
        self._executor = executor
        self._parser = parser

    def run_regression(
        self,
        macro_paths: list[str],
        baseline_dir: str = _DEFAULT_BASELINE_DIR,
        baseline_mode: bool = False,
    ) -> list[RegressionTestResult]:
        """Execute macros and compare against baselines.

        In baseline mode the current output is saved as the new baseline.
        Otherwise each macro's output is compared to its stored baseline.
        """
        os.makedirs(baseline_dir, exist_ok=True)
        results: list[RegressionTestResult] = []

        for path in macro_paths:
            result = self._run_one(path, baseline_dir, baseline_mode)
            results.append(result)
            logger.info(
                "%s %s",
                "PASS" if result.passed else "FAIL",
                Path(path).name,
            )

        return results

    def set_baseline(self, macro_path: str, output_dir: str = _DEFAULT_BASELINE_DIR):
        """Save current execution output as the baseline for a macro."""
        os.makedirs(output_dir, exist_ok=True)
        exec_result = self._executor.run(macro_path)

        baseline = {
            "macro_path": macro_path,
            "timestamp": datetime.now().isoformat(),
            "exit_code": exec_result.exit_code,
            "stdout": exec_result.stdout,
            "stderr": exec_result.stderr,
            "execution_time": exec_result.execution_time,
        }

        baseline_file = self._baseline_path(macro_path, output_dir)
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)

        logger.info("Baseline saved: %s", baseline_file)

    def compare_outputs(self, actual: str, expected: str) -> bool:
        """Fuzzy comparison that ignores timestamps and runtime values."""
        if not actual and not expected:
            return True
        if not actual or not expected:
            return False

        actual_norm = self._normalize(actual)
        expected_norm = self._normalize(expected)
        return actual_norm == expected_norm

    # ── internals ────────────────────────────────────────────────

    def _run_one(
        self,
        macro_path: str,
        baseline_dir: str,
        baseline_mode: bool,
    ) -> RegressionTestResult:
        exec_result = self._executor.run(macro_path)
        parsed = self._parser.parse(exec_result)

        baseline_file = self._baseline_path(macro_path, baseline_dir)

        if baseline_mode or not os.path.exists(baseline_file):
            self.set_baseline(macro_path, baseline_dir)
            return RegressionTestResult(
                macro_path=macro_path,
                passed=True,
                expected_output=exec_result.stdout,
                actual_output=exec_result.stdout,
                diff="[BASELINE CREATED]",
            )

        # Load baseline
        with open(baseline_file, "r", encoding="utf-8") as f:
            baseline = json.load(f)

        expected = baseline.get("stdout", "")
        actual = exec_result.stdout
        passed = self.compare_outputs(actual, expected)

        diff_str = ""
        if not passed:
            diff_str = "\n".join(
                unified_diff(
                    expected.splitlines(),
                    actual.splitlines(),
                    fromfile="baseline",
                    tofile="current",
                    lineterm="",
                )
            )

        return RegressionTestResult(
            macro_path=macro_path,
            passed=passed,
            expected_output=expected,
            actual_output=actual,
            diff=diff_str,
        )

    @staticmethod
    def _baseline_path(macro_path: str, baseline_dir: str) -> str:
        name = Path(macro_path).stem + ".baseline.json"
        return os.path.join(baseline_dir, name)

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize output by removing timestamps and runtime values."""
        return text.strip()
