"""zemax-debug CLI — run, test, and generate ZPL macros."""

import json
import sys
from pathlib import Path

import click

try:
    from zpl_toolkit.connection import ZemaxConnection, ConnectionException, LicenseException
    from zpl_toolkit.executor import ZPLExecutor
    from zpl_toolkit.parser import ZPLParser
    from zpl_toolkit.generator import ZPLGenerator
    from zpl_toolkit.manager import ZPLManager
    from zpl_toolkit.regression import RegressionRunner
    from zpl_toolkit.debug import ZPLDebugger
    from zpl_toolkit.types import ConnectionConfig
except ImportError as e:
    click.echo(click.style(f"Import error: {e}", fg="red"), err=True)
    click.echo("Install: pip install -e .", err=True)
    sys.exit(1)


# ── Shared helpers ──────────────────────────────────────────────

def _connect(config: ConnectionConfig) -> ZemaxConnection:
    """Connect to OpticStudio with friendly error messages."""
    try:
        conn = ZemaxConnection(config)
        conn.connect()
        return conn
    except ConnectionException as e:
        click.echo(click.style(f"Connection error: {e}", fg="red"), err=True)
        click.echo("Is OpticStudio installed?", err=True)
        sys.exit(1)
    except LicenseException as e:
        click.echo(click.style(f"License error: {e}", fg="red"), err=True)
        click.echo("ZOS-API requires Professional or Premium license.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Unexpected error: {e}", fg="red"), err=True)
        sys.exit(1)


def _report_result(result):
    """Print a single execution result with color."""
    status = "OK" if result.exit_code == 0 else f"FAIL({result.exit_code})"
    color = "green" if result.exit_code == 0 else "red"
    click.echo(
        click.style(f"{status}", fg=color) + f"  {result.macro_path}  "
        f"({result.execution_time:.2f}s)"
    )
    if result.stderr:
        click.echo(click.style(f"  stderr: {result.stderr[:200]}", fg="yellow"))


# ── Main CLI group ──────────────────────────────────────────────


@click.group()
@click.option("--config", "-c", default=None, help="Path to config file (unused, reserved)")
@click.option("--timeout", "-t", default=120, help="Execution timeout in seconds")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.version_option(version="0.1.0", prog_name="zemax-debug")
@click.pass_context
def main(ctx, config, timeout, verbose):
    """zemax-debug — ZPL macro automation tool for OpticStudio ZOS-API."""
    ctx.ensure_object(dict)
    ctx.obj["timeout"] = timeout
    ctx.obj["verbose"] = verbose


# ── run ─────────────────────────────────────────────────────────


@main.command()
@click.argument("macro_path", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Save stdout to file")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.pass_context
def run(ctx, macro_path, output, verbose):
    """Execute a ZPL macro in OpticStudio."""
    config = ConnectionConfig()
    timeout = ctx.obj.get("timeout", 120)

    with _connect(config) as zos:
        executor = ZPLExecutor(zos)
        result = executor.run(macro_path, timeout=timeout)

    _report_result(result)

    if verbose and result.stdout:
        click.echo("\n--- STDOUT ---")
        click.echo(result.stdout)
    if result.stderr:
        click.echo(click.style(f"\n--- STDERR ---\n{result.stderr}", fg="yellow"))

    if output and result.stdout:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result.stdout)
        click.echo(f"Output saved: {output}")

    sys.exit(result.exit_code if result.exit_code >= 0 else 1)


# ── test ────────────────────────────────────────────────────────


@main.command()
@click.option("--dir", "-d", "search_dir", required=True,
              type=click.Path(exists=True), help="Directory with ZPL macros")
@click.option("--recursive/--no-recursive", default=True, help="Search subdirectories")
@click.option("--baseline", is_flag=True, help="Create/update baselines instead of comparing")
@click.option("--report", "-r", default=None, help="Save JSON report to file")
@click.pass_context
def test(ctx, search_dir, recursive, baseline, report):
    """Batch test ZPL macros with regression comparison."""
    config = ConnectionConfig()
    timeout = ctx.obj.get("timeout", 120)

    manager = ZPLManager()
    macros = manager.discover(search_dir, recursive=recursive)

    if not macros:
        click.echo(click.style(f"No .ZPL files found in {search_dir}", fg="yellow"))
        return

    click.echo(f"Found {len(macros)} macros in {search_dir}")
    paths = [m.path for m in macros]

    with _connect(config) as zos:
        executor = ZPLExecutor(zos)
        parser = ZPLParser()
        runner = RegressionRunner(executor, parser)

        results = runner.run_regression(
            paths, baseline_mode=baseline
        )

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    click.echo()
    for r in results:
        color = "green" if r.passed else "red"
        status = "PASS" if r.passed else "FAIL"
        click.echo(click.style(f"  {status}", fg=color) + f"  {Path(r.macro_path).name}")
        if not r.passed and r.diff:
            for line in r.diff.splitlines()[:5]:
                click.echo(f"    {line}")

    click.echo(f"\n{passed} passed, {failed} failed, {len(results)} total")

    if report:
        report_data = {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "results": [
                {
                    "macro": r.macro_path,
                    "passed": r.passed,
                    "diff": r.diff if not r.passed else "",
                }
                for r in results
            ],
        }
        with open(report, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        click.echo(f"Report saved: {report}")

    sys.exit(1 if failed > 0 else 0)


# ── gen ─────────────────────────────────────────────────────────


@main.command()
@click.option("--type", "-t", "template_name", default=None, help="Template to use")
@click.option("--output", "-o", "output_file", default=None, help="Output file path")
@click.option("--params", "-p", default="", help="Comma-separated KEY=VALUE pairs")
@click.option("--list-templates", "list_mode", is_flag=True, help="List available templates")
@click.option("--dry-run", is_flag=True, help="Print to stdout, don't save")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing file")
@click.pass_context
def gen(ctx, template_name, output_file, params, list_mode, dry_run, force):
    """Generate ZPL code from templates."""
    generator = ZPLGenerator()

    if list_mode:
        click.echo("Available templates:")
        for t in generator.list_templates():
            req = [k for k, v in t.parameters.items() if v is None]
            opt = [k for k, v in t.parameters.items() if v is not None]
            click.echo(f"  {t.name}: {t.description}")
            if req:
                click.echo(f"    Required: {', '.join(req)}")
            if opt:
                click.echo(f"    Optional (defaults): {', '.join(f'{k}={v}' for k, v in t.parameters.items() if v is not None)}")
        return

    if not template_name:
        click.echo(click.style("Error: --type is required (use --list-templates to see options)", fg="red"))
        sys.exit(1)

    # Parse params
    param_dict = {}
    if params:
        for pair in params.split(","):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                param_dict[k.strip()] = v.strip()

    try:
        code = generator.generate(template_name, param_dict)
    except KeyError as e:
        click.echo(click.style(str(e), fg="red"))
        sys.exit(1)
    except ValueError as e:
        click.echo(click.style(str(e), fg="red"))
        sys.exit(1)

    if dry_run or not output_file:
        click.echo(code)
    else:
        try:
            path = generator.save(template_name, param_dict, output_file, force=force)
            click.echo(f"Generated: {path} ({len(code.splitlines())} lines)")
        except FileExistsError as e:
            click.echo(click.style(str(e), fg="yellow"))
            click.echo("Use --force to overwrite.")
            sys.exit(1)


# ── debug ───────────────────────────────────────────────────────


@main.command()
@click.argument("macro_path", type=click.Path(exists=True))
@click.pass_context
def trace(ctx, macro_path):
    """Trace ZPL execution with full diagnostic output."""
    config = ConnectionConfig()

    with _connect(config) as zos:
        executor = ZPLExecutor(zos)
        parser = ZPLParser()
        debugger = ZPLDebugger(zos, executor, parser)
        output = debugger.trace(macro_path)

    click.echo(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
