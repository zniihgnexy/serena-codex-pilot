#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

for command in git uv uvx rg node; do
  if ! command -v "$command" >/dev/null; then
    printf 'Install %s and add it to PATH.\n' "$command" >&2
    exit 1
  fi
done

tag=4.0.0
commit=b0de7a8d787b83c1fe0780e4960364e2171c8c36
target=.work/datasets
mkdir -p .work

if [[ ! -d "$target/.git" ]]; then
  git -c advice.detachedHead=false clone --depth 1 --branch "$tag" \
    https://github.com/huggingface/datasets.git "$target"
fi
if [[ "$(git -C "$target" rev-parse HEAD)" != "$commit" ]] ||
   [[ -n "$(git -C "$target" status --porcelain --untracked-files=no)" ]]; then
  printf 'Expected a clean Datasets checkout at %s in %s.\n' "$commit" "$target" >&2
  exit 1
fi

if [[ ! -x .work/venv/bin/python ]]; then
  uv venv --python 3.12 .work/venv
fi
uv pip install --python .work/venv/bin/python -e "$target"

if [[ ! -x .work/serena-venv/bin/python ]]; then
  uv venv --python 3.12 .work/serena-venv
fi
uv pip install --python .work/serena-venv/bin/python 'serena-agent==2.1.0'
uvx -p 3.13 --from 'pyright==1.1.403' pyright --version

printf '\nRun the fixture checks with:\n  .work/venv/bin/python scripts/pilot.py smoke\n'
