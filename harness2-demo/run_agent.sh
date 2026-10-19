#!/usr/bin/env bash
# 用真实模型跑 Harness² 自我进化：先复用 run.sh 准备好的环境，再运行 agent/llm_evolve.py。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.work/harness2/.venv/bin/python"
OUT="$HERE/.work/agent-k${K:-1}"

[ -x "$PY" ] || { echo "请先运行 ./run.sh 准备 Harness² 环境" >&2; exit 1; }
: "${DEEPSEEK_API_KEY:?需要设置 DEEPSEEK_API_KEY}"

"$PY" "$HERE/agent/llm_evolve.py" --output "$OUT" --k "${K:-1}"
python3 "$HERE/agent/report.py" "$OUT"
