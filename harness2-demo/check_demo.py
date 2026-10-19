"""运行 Harness² 离线 demo，打印并断言文章里的实测结论。只用标准库。"""

import argparse
import difflib
import json
import shutil
import subprocess
from pathlib import Path


def run_demo(bin_path: Path, out: Path, *args: str) -> dict:
    shutil.rmtree(out, ignore_errors=True)
    subprocess.run([str(bin_path), "--output", str(out), *args], check=True)
    return json.loads((out / "demo.json").read_text(encoding="utf-8"))


def step(n: int, title: str) -> None:
    print(f"\n== 第 {n} 步：{title}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, required=True, help="harness2-demo 可执行文件")
    parser.add_argument("--runs", type=Path, required=True, help="demo 输出目录")
    args = parser.parse_args()

    step(1, "k=1 并行模式，ledger-1 四次执行的答案")
    k1_dir = args.runs / "demo-k1"
    k1 = run_demo(args.bin, k1_dir, "--k", "1", "--mode", "parallel")
    execs = k1_dir / "executions" / "demo-oc-agg1" / "ledger-1"
    answers = {}
    for label in ("base1", "inv1", "dom1", "agg1"):
        answers[label] = (execs / label / "answer.txt").read_text(encoding="utf-8").strip()
        print(f"{label}: {answers[label]}")
    print(f"execution_count={k1['execution_count']} editor_calls={k1['editor_calls']}")
    assert answers["base1"] == "Total: 105.25", "基线应漏掉贷方金额"
    assert all(answers[x] == "Total: 85.15" for x in ("inv1", "dom1", "agg1"))
    assert (k1["execution_count"], k1["editor_calls"]) == (8, 8), "k=1 每个任务应执行 4 次"

    step(2, "被采纳的 harness 与基线的差异")
    entry = k1_dir / "library" / "k1" / "agg" / "accounting" / "harnesses" / "ledger-1"
    base_script = (k1_dir / "base" / "scripts" / "summarize.py").read_text(encoding="utf-8")
    new_script = (entry / "harness" / "scripts" / "summarize.py").read_text(encoding="utf-8")
    diff = list(difflib.unified_diff(
        base_script.splitlines(), new_script.splitlines(), "base", "adopted", lineterm=""))
    print("\n".join(diff))
    assert "if amount > 0" in base_script and "if amount > 0" not in new_script

    step(3, "经验库里的 EXPERIENCE.md")
    experience = (entry / "EXPERIENCE.md").read_text(encoding="utf-8")
    print(experience)
    for field in ("cue", "lesson", "evidence"):
        assert f"- **{field}**:" in experience, f"经验缺少 {field}"
    assert "without a selector session" in experience, "k=1 不应调用选择器"

    step(4, "k=2 两种模式，执行次数与经验库")
    k2 = run_demo(args.bin, args.runs / "demo-k2", "--k", "2")
    before = {t["task"]: t["library_entries_before"] for t in k2["tasks"]}
    print(f"execution_count={k2['execution_count']} editor_calls={k2['editor_calls']}")
    print(f"library_entries_before={json.dumps(before, sort_keys=True)}")
    assert (k2["execution_count"], k2["editor_calls"]) == (28, 32), "两种模式共用 2 次参照执行"
    assert before["ledger-1"] == {"agg": 0, "seq": 0}
    assert before["ledger-2"] == {"agg": 1, "seq": 1}, "第二个任务开始前库里应有 1 条"

    print("\n全部断言通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
