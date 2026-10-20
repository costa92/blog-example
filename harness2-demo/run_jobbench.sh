#!/usr/bin/env bash
# 用 DeepSeek 跑 Harness² 自带的 JobBench 适配器：一步改进、裁判打分、报告，再给两个候选打分。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/.work"
SRC="$WORK/harness2"
DOMAIN="${DOMAIN:-bookkeeping_accounting_and_auditing_clerks}"
ARGS=(--bench jb --k 1 --mode parallel)

[ -x "$SRC/.venv/bin/harness2" ] || { echo "请先运行 ./run.sh 准备 Harness² 环境" >&2; exit 1; }
: "${DEEPSEEK_API_KEY:?需要设置 DEEPSEEK_API_KEY}"

# OpenCode 会加载 ~/.config/opencode 的插件和 ~/.claude/skills 等目录的技能，换成独立目录避免污染执行器。
mkdir -p "$WORK/jb-home" "$WORK/jb-config/opencode"
cp "$HERE/jobbench/opencode.json" "$WORK/jb-config/opencode/opencode.json"
export HOME="$WORK/jb-home" XDG_CONFIG_HOME="$WORK/jb-config"
export HARNESS2_SOLVER_MODEL="${HARNESS2_SOLVER_MODEL:-deepseek/deepseek-flash}"
export HARNESS2_IMPROVER_MODEL="${HARNESS2_IMPROVER_MODEL:-deepseek/deepseek-v4-pro}"
export HARNESS2_JUDGE_MODEL="${HARNESS2_JUDGE_MODEL:-deepseek-v4-pro}"
export HARNESS2_JUDGE_BASE_URL="${HARNESS2_JUDGE_BASE_URL:-https://api.deepseek.com}"
export HARNESS2_JUDGE_API_KEY="${HARNESS2_JUDGE_API_KEY:-$DEEPSEEK_API_KEY}"
export HARNESS2_RUNS_DIR="$WORK/jb-runs"

cd "$SRC"
# shellcheck disable=SC1091
source .venv/bin/activate
[ -d dependencies/job-bench-eval/dataset/main ] || harness2-setup jb
harness2-check --bench jb
harness2 "${ARGS[@]}" --only-domains "$DOMAIN" --max-tasks 1
harness2-judge "${ARGS[@]}"
harness2-judge "${ARGS[@]}" --bases
harness2-report "${ARGS[@]}"
python "$HERE/jobbench/judge_candidates.py" "$DOMAIN"
