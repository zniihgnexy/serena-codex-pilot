import argparse
import collections
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".work"
UPSTREAM = WORK / "datasets"
UPSTREAM_COMMIT = "b0de7a8d787b83c1fe0780e4960364e2171c8c36"
SERENA = WORK / "serena-venv/bin/serena"
SERENA_ARGS = [
    "start-mcp-server", "--context=codex", "--project-from-cwd",
    "--language-backend=LSP", "--agent-interface=tools",
    "--open-web-dashboard=false", "--enable-web-dashboard=false", "--enable-gui-log-window=false",
]
TASKS = tuple(sorted((ROOT / "tasks").glob("*.md")))
REGRESSION = "03-regression"
ORIGINAL = "pa_subtable = query_table(self._data, key, indices=self._indices)"
REGRESSED = "pa_subtable = query_table(self._data, key)"


def git(checkout, *args):
    return subprocess.check_output(["git", "-C", checkout, *args], text=True).strip()


def fixture_env(checkout):
    return {
        **os.environ,
        "PATH": f"{WORK / 'venv/bin'}{os.pathsep}{os.environ.get('PATH', '')}",
        "PYTHONPATH": str(checkout / "src"),
        "HF_HUB_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
    }


def indexing_check(checkout):
    return subprocess.run(
        [WORK / "venv/bin/python", ROOT / "scripts/check_indexing.py"],
        cwd=checkout,
        env=fixture_env(checkout),
        capture_output=True,
        text=True,
    )


def serena_environment(home):
    home.mkdir()
    pyright = json.dumps(str(SERENA.with_name("pyright-langserver")))
    (home / "serena_config.yml").write_text(
        f"projects: []\nls_specific_settings:\n  python:\n    ls_path: {pyright}\n",
        encoding="utf-8",
    )
    return {"SERENA_HOME": str(home)}


def prepare(checkout, *, regression):
    subprocess.run(
        ["git", "-c", "advice.detachedHead=false", "clone", "--quiet", "--no-hardlinks", UPSTREAM, checkout],
        check=True,
    )
    if git(checkout, "rev-parse", "HEAD") != UPSTREAM_COMMIT:
        raise RuntimeError("Datasets checkout is at the wrong commit. Run scripts/setup.sh.")
    with (checkout / ".git/info/exclude").open("a", encoding="utf-8") as exclude:
        exclude.write("\n/.serena/\n")
    if regression:
        file = checkout / "src/datasets/arrow_dataset.py"
        source = file.read_text(encoding="utf-8")
        if source.count(ORIGINAL) != 1:
            raise RuntimeError("The regression fixture no longer matches the pinned source.")
        file.write_text(source.replace(ORIGINAL, REGRESSED), encoding="utf-8")


def smoke():
    clean = indexing_check(UPSTREAM)
    if clean.returncode:
        raise RuntimeError(clean.stderr)

    with tempfile.TemporaryDirectory(prefix="smoke-", dir=WORK) as folder:
        checkout = Path(folder) / "checkout"
        prepare(checkout, regression=True)
        regressed = indexing_check(checkout)
        if regressed.returncode != 1 or "AssertionError: {'id': 10}" not in regressed.stderr:
            raise RuntimeError(f"Expected the wrong-row assertion, got:\n{regressed.stderr}")
        subprocess.run(
            ["git", "-C", checkout, "restore", "src/datasets/arrow_dataset.py"], check=True
        )
        restored = indexing_check(checkout)
        if restored.returncode:
            raise RuntimeError(restored.stderr)
    print("PASS: pinned source, seeded wrong-row regression, and restored source.")


def read_events(path):
    usage = collections.Counter()
    tool_items = {}
    completed = False
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed":
            completed = True
            usage.update(event.get("usage") or {})
        item = event.get("item") or {}
        if item.get("type") in {"command_execution", "mcp_tool_call", "web_search"}:
            tool_items[item["id"]] = item

    return {
        "turn_completed": completed,
        "usage": dict(usage) if usage else None,
        "terminal_calls": sum(item["type"] == "command_execution" for item in tool_items.values()),
        "mcp_calls": sum(item["type"] == "mcp_tool_call" for item in tool_items.values()),
        "serena_calls": sum(item.get("server") == "serena" for item in tool_items.values()),
        "serena_successful_calls": sum(
            item.get("server") == "serena"
            and item.get("status") == "completed"
            and not item.get("error")
            and not (item.get("result") or {}).get("isError")
            and not (item.get("result") or {}).get("is_error")
            for item in tool_items.values()
        ),
        "web_searches": sum(item["type"] == "web_search" for item in tool_items.values()),
    }


def run_case(args, task, condition, repeat, run_root, version):
    case = run_root / f"{repeat:02d}-{task.stem}-{condition}"
    case.mkdir()
    checkout = case / "checkout"
    is_regression = task.stem == REGRESSION
    prepare(checkout, regression=is_regression)

    mcp = "{}"
    if condition == "serena":
        env = serena_environment(case / "serena-home")
        serena_home = json.dumps(env["SERENA_HOME"])
        mcp = (
            f"{{serena={{command={json.dumps(str(SERENA))}, args={json.dumps(SERENA_ARGS)}, "
            f"env={{SERENA_HOME={serena_home}}}, startup_timeout_sec=90}}}}"
        )

    command = [
        "codex", "-a", "never", "-c", f"mcp_servers={mcp}",
        "-c", 'web_search="disabled"', "-c", "features.hooks=false",
        "-c", f"model_reasoning_effort={json.dumps(args.effort)}",
        "exec", "--ephemeral", "--json", "--model", args.model,
        "--sandbox", "workspace-write" if is_regression else "read-only",
        "--output-last-message", str(case / "answer.md"), "-",
    ]
    timeout = False
    events = case / "events.jsonl"
    with events.open("w", encoding="utf-8") as stdout, (case / "stderr.log").open("w", encoding="utf-8") as stderr:
        started = time.monotonic()
        try:
            result = subprocess.run(
                command, input=task.read_text(encoding="utf-8"), text=True,
                cwd=checkout, env=fixture_env(checkout), stdout=stdout, stderr=stderr,
                timeout=args.timeout,
            )
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            returncode = None
            timeout = True
        seconds = round(time.monotonic() - started, 2)

    diff = git(checkout, "diff", "HEAD")
    (case / "changes.diff").write_text(diff + "\n" if diff else "", encoding="utf-8")
    check = indexing_check(checkout) if is_regression else None
    if check is not None:
        (case / "check.log").write_text(check.stdout + check.stderr, encoding="utf-8")

    metrics = {
        "task": task.stem, "condition": condition, "repeat": repeat,
        "model": args.model, "effort": args.effort, "codex_version": version,
        "datasets_commit": UPSTREAM_COMMIT,
        "serena_version": "2.1.0" if condition == "serena" else None,
        "seconds": seconds, "returncode": returncode, "timeout": timeout,
        "changed": bool(git(checkout, "status", "--porcelain")),
        "regression_passed": check.returncode == 0 if check is not None else None,
        **read_events(events),
    }
    (case / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"{case.name}: {seconds:.2f}s, exit={returncode}, finished={metrics['turn_completed']}", flush=True)
    return metrics


def run(args):
    tasks = [task for task in TASKS if args.task == "all" or task.stem == args.task]
    conditions = ("baseline", "serena") if args.condition == "both" else (args.condition,)
    if "serena" in conditions and not all(
        binary.is_file() for binary in (SERENA, SERENA.with_name("pyright-langserver"))
    ):
        raise RuntimeError("Serena or Pyright is missing. Run scripts/setup.sh.")
    version = subprocess.check_output(["codex", "--version"], text=True).strip()
    runs = WORK / "runs"
    runs.mkdir(exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="pilot-", dir=runs))
    print(f"Run output: {run_root.relative_to(ROOT)}", flush=True)
    summary = run_root / "summary.jsonl"
    failures = False
    with summary.open("w", encoding="utf-8") as output:
        for repeat in range(1, args.repeats + 1):
            order = conditions if repeat % 2 else conditions[::-1]
            for task in tasks:
                for condition in order:
                    metrics = run_case(args, task, condition, repeat, run_root, version)
                    output.write(json.dumps(metrics) + "\n")
                    output.flush()
                    failures |= metrics["returncode"] != 0 or not metrics["turn_completed"]
    return int(failures)


def main():
    parser = argparse.ArgumentParser(description="Run the Serena + Codex pilot on a pinned Python repo.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("smoke", help="Check the local fixture without running Codex.")
    bench = commands.add_parser("run", help="Run fresh Codex sessions and collect their metrics.")
    bench.add_argument("--model", required=True)
    bench.add_argument("--effort", default="medium", choices=("low", "medium", "high", "xhigh"))
    bench.add_argument("--condition", default="both", choices=("both", "baseline", "serena"))
    bench.add_argument("--task", default="all", choices=("all", *(task.stem for task in TASKS)))
    bench.add_argument("--repeats", type=int, default=1)
    bench.add_argument("--timeout", type=int, default=600, help="Per-session limit in seconds.")
    args = parser.parse_args()
    if not (UPSTREAM / ".git").is_dir() or not (WORK / "venv/bin/python").is_file():
        parser.error("Run scripts/setup.sh first.")
    if args.command == "smoke":
        smoke()
        return 0
    if args.repeats < 1 or args.timeout < 1:
        parser.error("--repeats and --timeout must be positive.")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
