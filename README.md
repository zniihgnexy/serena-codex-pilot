# Serena × Codex on a real Python codebase

Does semantic code navigation help Codex work through a large Python repository? Run the same three tasks with and without [Serena](https://github.com/oraios/serena) on a pinned checkout of [Hugging Face Datasets](https://github.com/huggingface/datasets), then compare correctness, token usage, tool calls, and elapsed time.

## Quick start

Use Ubuntu or another Linux environment with Git, `rg`, `uv`, and a signed-in [Codex CLI](https://developers.openai.com/codex/cli). Setup fetches the public source and installs Datasets, Serena, and Pyright with a bundled Node.js runtime into local Python 3.12 environments. The tasks use local fixtures and need no GPU or Hugging Face credentials.

```bash
bash scripts/setup.sh
.work/venv/bin/python scripts/pilot.py smoke
.work/serena-venv/bin/python scripts/check_serena.py
```

Run the first comparison. Replace `gpt-5.4` with an available Codex model if needed.

```bash
.work/venv/bin/python scripts/pilot.py run --model gpt-5.4 --task 01-cli
```

Run all tasks with two repetitions per condition, for a total of 12 model sessions.

```bash
.work/venv/bin/python scripts/pilot.py run --model gpt-5.4 --repeats 2
```

## Tasks

| Task | Outcome |
| --- | --- |
| [CLI trace](tasks/01-cli.md) | Follow `--num_proc` from console entry point to the builder API. |
| [Call sites](tasks/02-references.md) | Find all direct production callers of `query_table` and explain their roles. |
| [Regression repair](tasks/03-regression.md) | Fix incorrect row ordering after a non-contiguous selection and pass the in-memory check. |

## How to compare

- The runner uses fresh Codex sessions and clean copies of Datasets `4.0.0` (`b0de7a8d`). Both conditions receive the same prompt, model, reasoning effort, and time limit. The first two tasks use a read-only shell sandbox. The third starts with the same seeded change and permits edits to its disposable checkout.
- The baseline uses Codex's standard local tools. The Serena condition adds Serena `2.1.0` with Pyright `1.1.403` and keeps the same local tools. Each Serena run gets its own configuration and project state. Timing includes session and language server startup. The condition order reverses on every second repeat.
- Use the [scoring rubric](results/rubric.md) for the two read-only answers. The runner checks the repair against [`check_indexing.py`](scripts/check_indexing.py). Count a repair as correct only when the agent finishes, the check passes, and the patch addresses the regression.
- Start with success counts. Compare input, cached input, and output tokens separately for successful pairs. Missing usage appears as `null`. Treat terminal calls and MCP calls as separate counts and check `serena_successful_calls` before attributing changes to Serena. Cache hits and startup time can vary, so keep the run order and model versions with any figures you share.

The runner writes `summary.jsonl` under the `.work/runs/` directory it prints. Each case also saves `answer.md` when available, `metrics.json`, `events.jsonl`, `stderr.log`, and `changes.diff`. The repair includes `check.log`. These files stay local and are ignored by Git. Share reviewed summaries instead of raw session logs.

See [verification status](results/README.md) for the latest checks and the status of model comparisons.
