"""读 llm_evolve.py 的输出目录，打印每个任务的进化前后对比。只用标准库。"""

import argparse
import difflib
import json
from pathlib import Path


def answer(run_dir: Path) -> str:
    p = run_dir / "answer.txt"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else "(no answer)"


def base_file(root: Path, f: Path, entry: Path) -> str:
    b = root / "base" / f.relative_to(entry / "harness")
    return b.read_text(encoding="utf-8") if b.is_file() else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--brief", action="store_true", help="不打印 diff 和 harness 文件内容")
    args = parser.parse_args()
    root = args.output
    result = json.loads((root / "result.json").read_text(encoding="utf-8"))
    execs = next((root / "executions").glob("ledger-oc-agg*"))
    lib = root / "library" / "agg" / "accounting" / "harnesses"
    base_script = (root / "base" / "scripts" / "summarize.py").read_text(encoding="utf-8")

    ok = True
    earlier: list[str] = []
    for t in result["tasks"]:
        tid = t["task"]
        print(f"\n== {tid}（开始前经验库 {t['library_entries_before']['agg']} 条）")
        print(f"标准答案: {result['truth'][tid]}")
        for d in sorted((execs / tid).iterdir()):
            steps = (d / "trajectory.md").read_text(encoding="utf-8").count("[ACTION]")
            print(f"{d.name}: {answer(d)}（{steps} 次工具调用）")
        reads = sum(
            f.read_text(encoding="utf-8").count('[ACTION] read_file {"path": "context/library')
            for f in (root / "editor" / tid).glob("*/trajectory.md")
        )
        print(f"编辑器读取经验库文件 {reads} 次")
        entry = lib / tid
        if not entry.is_dir():
            print("未入库")
            ok = False
            continue
        adopted = (entry / "EXPERIENCE.md").read_text(encoding="utf-8").splitlines()[2]
        label = adopted.split("`")[1]
        final = answer(execs / tid / label)
        print(f"采纳 {label}: {final} {'✓' if final == result['truth'][tid] else '✗'}")
        ok &= final == result["truth"][tid]
        script = entry / "harness" / "scripts" / "summarize.py"
        files = sorted(str(f.relative_to(entry / "harness")) for f in (entry / "harness").rglob("*")
                       if f.is_file() and f.read_text(encoding="utf-8") != base_file(root, f, entry))
        print(f"相对基线改动的文件: {', '.join(files) or '无'}")
        same = [e for e in earlier if script.is_file()
                and (lib / e / "harness/scripts/summarize.py").is_file()
                and (lib / e / "harness/scripts/summarize.py").read_bytes() == script.read_bytes()]
        earlier.append(tid)
        if same:
            print(f"scripts/summarize.py 与 {', '.join(same)} 采纳的版本逐字节相同")
        if args.brief:
            continue
        if script.is_file():
            new = script.read_text(encoding="utf-8")
            print("\n".join(difflib.unified_diff(
                base_script.splitlines(), new.splitlines(), "base", label, lineterm="")))
        for f in sorted((entry / "harness").rglob("*")):
            if f.is_file() and f.suffix == ".md" and f.read_text(encoding="utf-8").strip():
                print(f"-- {f.relative_to(entry / 'harness')} --")
                print(f.read_text(encoding="utf-8").strip()[:1200])
        print("-- EXPERIENCE.md（Transferable lesson）--")
        text = (entry / "EXPERIENCE.md").read_text(encoding="utf-8")
        print(text[text.find("## Transferable lesson"):].strip())

    u = result["usage"]
    for role in ("executor", "editor"):
        print(f"{role}: {u[role]['calls']} 次调用，输入 {u[role]['prompt']} tokens，输出 {u[role]['completion']} tokens")
    print("全部任务采纳版答对" if ok else "有任务采纳版答错")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
