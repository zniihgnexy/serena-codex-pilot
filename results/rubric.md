# Scoring rubric

Grade the saved answers after the runs. Paths below are relative to the Datasets checkout at `b0de7a8d787b83c1fe0780e4960364e2171c8c36`.

## 01 — CLI trace

Pass when the answer follows the argument through these stages in order and supplies accurate file and line references. The read-only checkout should remain unchanged.

| Stage | Evidence |
| --- | --- |
| Console script | `setup.py:247` maps `datasets-cli` to `datasets.commands.datasets_cli:main`. |
| Registration and parsing | `src/datasets/commands/datasets_cli.py:23` registers `TestCommand`. At line 27 it parses the arguments. In `src/datasets/commands/test.py:69`, `--num_proc` is parsed as an integer, and line 73 selects `_test_command_factory`. |
| Dispatch and storage | `src/datasets/commands/datasets_cli.py:34–35` creates and runs the command. The factory passes `args.num_proc` at `src/datasets/commands/test.py:20–31`, and the constructor stores it in `self._num_proc` at line 97. |
| Builder call | `TestCommand.run` passes `num_proc=self._num_proc` at `src/datasets/commands/test.py:150–157` to `DatasetBuilder.download_and_prepare`, defined at `src/datasets/builder.py:691`. |

## 02 — Direct references

Record the number of correct sites out of 12 and the number of false positives. Pass requires all 12 sites, accurate enclosing functions and purposes, and no changes to the checkout.

| File | Enclosing functions and call lines |
| --- | --- |
| `src/datasets/arrow_dataset.py` | `Dataset._getitem` (2840, slice/index lookup), `Dataset.sort` (4453, sort keys), `Dataset.to_dict` (5042, whole-table conversion), `Dataset.to_list` (5060, conversion to rows), `Dataset.to_pandas` (5151 and 5159, full and batched conversions), `Dataset.to_polars` (5202 and 5214, full and batched conversions). |
| `src/datasets/io/csv.py` | `CsvDatasetWriter._batch_csv` (105, CSV export batch). |
| `src/datasets/io/json.py` | `JsonDatasetWriter._batch_json` (129, JSON export batch). |
| `src/datasets/io/parquet.py` | `ParquetDatasetWriter._write` (114, Parquet row batch). |
| `src/datasets/io/sql.py` | `SqlDatasetWriter._batch_sql` (87, SQL export batch). |

## 03 — Repair

Check for a completed model turn and `regression_passed: true`. Inspect the resulting `changes.diff`. An empty tracked diff is expected when the agent restores the original code by passing `self._indices` into `query_table`. A different patch can pass if it fixes the same index mapping for both selected and unselected datasets. The fixture checks individual rows, negative indices, slices, batches, and NumPy formatting.
