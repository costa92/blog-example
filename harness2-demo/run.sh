#!/usr/bin/env bash
# 拉取固定版本的 Harness²，建 Python 3.12 环境，运行离线 demo 并校验文中结论。
set -euo pipefail

HARNESS2_COMMIT=1cfe254e8d25b15f37048c3730134686abe60335
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/.work"
SRC="$WORK/harness2"

for cmd in git uv; do
  command -v "$cmd" >/dev/null || { echo "缺少命令：$cmd" >&2; exit 1; }
done

if [ ! -d "$SRC/.git" ]; then
  mkdir -p "$WORK"
  git clone -q https://github.com/google-research/harness2 "$SRC"
fi
git -C "$SRC" fetch -q origin "$HARNESS2_COMMIT"
git -C "$SRC" checkout -q "$HARNESS2_COMMIT"

if [ ! -x "$SRC/.venv/bin/harness2-demo" ]; then
  uv venv -q --python 3.12 "$SRC/.venv"
  VIRTUAL_ENV="$SRC/.venv" uv pip install -q -e "$SRC[render]"
fi

python3 "$HERE/check_demo.py" --bin "$SRC/.venv/bin/harness2-demo" --runs "$WORK/runs"
