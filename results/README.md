# Verification and results

| Check | Outcome |
| --- | --- |
| Pinned Datasets fixture | The upstream source passed the in-memory indexing check. The seeded regression returned the wrong row and failed the same check. Restoring the original source passed. |
| CLI path | A local one-shard CSV run reached the builder and completed. The builder reported the expected reduction from two workers to one because the fixture had one shard. |
| Serena MCP and Pyright | `check_serena.py` found `Dataset/_getitem` in the pinned checkout using Serena's `find_symbol` tool. |
| Codex baseline and Serena comparison | Both launch attempts stopped before a model turn. Codex CLI `0.172.0-alpha.2` reported `Read-only file system (os error 30)` while initializing its app-server client in the execution environment. |

The model comparison has no correctness, token, or elapsed-time results to report. Only include successful model turns in the paired results table and retain failed-session counts alongside it.
