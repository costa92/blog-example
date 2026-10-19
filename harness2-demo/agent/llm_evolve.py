"""用真实模型跑 Harness² 的自我进化：执行器与编辑器都是工具调用 Agent。

Harness² 的递归、选择和经验库原样调用（harness2.core.schedule.run_domain），
这里只替换两处模型调用：
- LedgerAdapter.execute：执行器 Agent 带着当前 harness 做对账任务；
- LLMProposer.call：编辑器 Agent 读证据、改 context/harness/，以及做选择和经验提炼。
两者都走 OpenAI 兼容的 /chat/completions，只用标准库。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from harness2.core import tree
from harness2.core.proposer import Proposer, Reply
from harness2.core.schedule import run_domain
from harness2.core.spec import BenchPrompts, BenchSpec, ChannelSpec
from harness2.substrate.opencode import OpencodeSubstrate

HERE = Path(__file__).resolve().parent

# 基线脚本的 bug：解析失败的行被静默跳过，括号负数 (20.10) 与尾随负号 15.00- 都会漏掉。
BASE_SCRIPT = """import csv
import sys
from decimal import Decimal, InvalidOperation

total = Decimal(0)
with open(sys.argv[1]) as source:
    for row in csv.DictReader(source):
        try:
            total += Decimal(row['amount'].replace(',', ''))
        except InvalidOperation:
            continue
print(f'Total: {total:.2f}')
"""

BASE_PROMPT = (
    "You reconcile transaction ledgers.\n"
    "Run `python3 scripts/summarize.py ledger.csv` and write the Total line it prints "
    "to answer.txt, exactly as printed.\n"
)


@dataclass
class Model:
    role: str
    base_url: str
    model: str
    key_env: str
    usage: dict = field(default_factory=lambda: {"calls": 0, "prompt": 0, "completion": 0})

    def chat(self, messages: list, tools: list) -> dict:
        body = json.dumps({"model": self.model, "messages": messages, "tools": tools}).encode()
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {os.environ[self.key_env]}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=600) as resp:
                    data = json.load(resp)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        u = data.get("usage") or {}
        self.usage["calls"] += 1
        self.usage["prompt"] += u.get("prompt_tokens", 0)
        self.usage["completion"] += u.get("completion_tokens", 0)
        return data["choices"][0]["message"]


def _tool(name: str, desc: str, **props: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
                "required": list(props),
            },
        },
    }


TOOLS = [
    _tool("list_files", "List files under a directory, relative to the workspace.", path="dir"),
    _tool("read_file", "Read a text file, relative to the workspace.", path="file path"),
    _tool("write_file", "Create or overwrite a text file.", path="file path", content="text"),
    _tool(
        "run_python",
        "Run `python3 <script> <args>` in the workspace and return stdout and stderr.",
        script="script path",
        args="space-separated arguments, may be empty",
    ),
]


def run_agent(model: Model, root: Path, system: str, user: str, max_steps: int) -> tuple[str, list]:
    """最小工具调用循环：返回最终回复与 [ACTION]/[OBSERVATION] 轨迹。"""

    def inside(p: str) -> Path:
        path = (root / p).resolve()
        if path != root and root not in path.parents:
            raise ValueError(f"path escapes the workspace: {p}")
        return path

    def call(name: str, a: dict) -> str:
        if name == "list_files":
            base = inside(a.get("path") or ".")
            return "\n".join(
                str(p.relative_to(root)) for p in sorted(base.rglob("*")) if p.is_file()
            )
        if name == "read_file":
            return inside(a["path"]).read_text(encoding="utf-8", errors="replace")[:50_000]
        if name == "write_file":
            path = inside(a["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(a["content"], encoding="utf-8")
            return f"wrote {a['path']}"
        if name == "run_python":
            p = subprocess.run(
                [sys.executable, str(inside(a["script"])), *(a.get("args") or "").split()],
                cwd=root, capture_output=True, text=True, timeout=60,
            )
            return (p.stdout + p.stderr)[:20_000] or f"(exit {p.returncode}, no output)"
        raise ValueError(f"unknown tool {name}")

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    trace: list[str] = []
    for _ in range(max_steps):
        msg = model.chat(messages, TOOLS)
        messages.append({k: v for k, v in msg.items() if v is not None})
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content") or "", trace
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
                out = call(name, args)
                trace.append(f"[ACTION] {name} {json.dumps(args, ensure_ascii=False)[:2000]}")
                trace.append(f"[OBSERVATION]\n{out[:4000]}")
            except Exception as exc:
                out = f"error: {type(exc).__name__}: {exc}"
                trace.append(f"[ACTION] {name}\n[ERROR] {out}")
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": out})
    return "", trace + ["[ERROR] step limit reached"]


TASKS = {
    "ledger-1": ["1,250.00", "(20.10)", "5.00", "(300.00)", "42.50"],
    "ledger-2": ["(1,000.00)", "15.00-", "2,400.00", "(80.25)", "7.75"],
}


def truth(amounts: list[str]) -> Decimal:
    """标准答案只给本脚本做校验，不进入任何 Agent 的上下文。"""
    total = Decimal(0)
    for a in amounts:
        a = a.replace(",", "")
        neg = a.startswith("(") or a.endswith("-")
        total += -Decimal(a.strip("()-")) if neg else Decimal(a)
    return total


class LedgerAdapter:
    def __init__(self, root: Path, executor: Model):
        self.root = root
        self.executor = executor
        self.substrate = OpencodeSubstrate()
        ch = ChannelSpec("opencode", "local/agent")
        self.spec = BenchSpec(
            name="ledger",
            runs_root=root / "runs",
            install_mode="workspace_config",
            prompts=BenchPrompts(
                work="reconcile signed amounts in transaction ledgers exported by accounting "
                "systems, which write negatives in several notations"
            ),
            channels={"proposer": ch, "selector": ch},
        )
        base = {name: "" for name in self.substrate.surface().always_on}
        base["systemprompt.md"] = BASE_PROMPT
        base["scripts/summarize.py"] = BASE_SCRIPT
        tree.write_tree(self.substrate.surface(), base, self.base_harness(), stubs=False)
        for task_id, amounts in TASKS.items():
            src = self.task_files(task_id)
            src.mkdir(parents=True, exist_ok=True)
            rows = "".join(f'"{a}"\n' for a in amounts)
            (src / "ledger.csv").write_text("amount\n" + rows, encoding="utf-8")

    def tasks(self, split: str = "all") -> list[str]:
        return list(TASKS)

    def domain_of(self, task_id: str) -> str:
        return "accounting"

    def task_prompt(self, task_id: str) -> str:
        return "Sum every signed amount in ledger.csv. Write `Total: <sum>` with two decimals to answer.txt."

    def task_files(self, task_id: str) -> Path:
        return self.root / "sources" / task_id

    def base_harness(self) -> Path:
        return self.root / "base"

    def validate_tree(self, harness: tree.Tree) -> None:
        if not harness.get("systemprompt.md", "").strip():
            raise ValueError("systemprompt.md must not be empty")

    def execute(self, task_id: str, harness_dir: Path | None, run_id: str, *, timeout=None) -> Path:
        run_dir = self.root / "executions" / run_id
        if (run_dir / "trajectory.md").is_file():
            return run_dir
        ws = run_dir / "workspace"
        shutil.rmtree(ws, ignore_errors=True)
        shutil.copytree(self.task_files(task_id), ws)
        hdir = harness_dir or self.base_harness()
        if (hdir / "scripts").is_dir():
            shutil.copytree(hdir / "scripts", ws / "scripts")
        if (hdir / "skills").is_dir():
            shutil.copytree(hdir / "skills", ws / "skills")
        system = "\n\n".join(
            (hdir / f).read_text(encoding="utf-8")
            for f in self.substrate.surface().always_on
            if (hdir / f).is_file() and (hdir / f).read_text(encoding="utf-8").strip()
        )
        _, trace = run_agent(self.executor, ws, system, self.task_prompt(task_id), max_steps=15)
        if (ws / "answer.txt").is_file():
            shutil.copy(ws / "answer.txt", run_dir / "answer.txt")
        (run_dir / "trajectory.md").write_text("\n".join(trace), encoding="utf-8")
        return run_dir

    def delivered(self, run_dir: Path) -> bool:
        return (run_dir / "answer.txt").is_file()

    def trajectory(self, run_dir: Path, *, obs_trunc: int) -> str:
        return (run_dir / "trajectory.md").read_text(encoding="utf-8")

    def deliverable_text(self, run_dir: Path) -> str:
        return (run_dir / "answer.txt").read_text(encoding="utf-8")

    def deliverable_files(self, run_dir: Path) -> dict[str, str]:
        return {"answer.txt": self.deliverable_text(run_dir)}


EDITOR_SYSTEM = (
    "You work inside a workspace whose files are under context/. Use the tools to read the "
    "evidence and, when the mission asks for harness edits, edit the files in "
    "context/harness/ in place with write_file. You may test scripts with run_python. "
    "Finish with a final message in exactly the format the mission requests."
)


class LLMProposer(Proposer):
    """把编辑器、选择器、经验提炼三类会话都交给编辑器模型。"""

    def __init__(self, editor: Model, audit_dir: Path):
        super().__init__(ChannelSpec("opencode", "local/agent"), audit_dir=audit_dir)
        self.editor = editor

    def call(self, mission, context_dir, label, *, harvest=None, **kwargs) -> Reply:
        tmp = Path(tempfile.mkdtemp(prefix="h2-llm-"))
        try:
            if context_dir and Path(context_dir).is_dir():
                shutil.copytree(context_dir, tmp / "context")
            t0 = time.time()
            text, trace = run_agent(self.editor, tmp, EDITOR_SYSTEM, mission, max_steps=40)
            workspace = None
            task = next((part for part in Path(str(context_dir)).parts if part in TASKS), "_")
            out = Path(self.audit_dir) / task / label
            shutil.rmtree(out, ignore_errors=True)
            out.mkdir(parents=True)
            (out / "trajectory.md").write_text("\n".join(trace), encoding="utf-8")
            (out / "reply.md").write_text(text, encoding="utf-8")
            if harvest and (tmp / harvest).is_dir():
                workspace = out / "workspace"
                shutil.copytree(tmp / harvest, workspace)
            reply = Reply(
                label=label, text=text, ok=bool(text.strip()), attempts=1,
                wall_s=round(time.time() - t0, 1), workspace=workspace,
            )
            self._calls.append(reply)
            return reply
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def model_from_env(role: str, base_url: str, model: str, key_env: str) -> Model:
    p = role.upper()
    return Model(
        role,
        os.environ.get(f"{p}_BASE_URL", base_url),
        os.environ.get(f"{p}_MODEL", model),
        os.environ.get(f"{p}_KEY_ENV", key_env),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--k", type=int, default=1)
    args = parser.parse_args()

    executor = model_from_env("executor", "https://api.deepseek.com", "deepseek-flash", "DEEPSEEK_API_KEY")
    editor = model_from_env("editor", "https://api.deepseek.com", "deepseek-v4-pro", "DEEPSEEK_API_KEY")
    for m in (executor, editor):
        if not os.environ.get(m.key_env):
            sys.exit(f"缺少环境变量 {m.key_env}（{m.role} 使用 {m.model}）")

    root = args.output.resolve()
    shutil.rmtree(root, ignore_errors=True)
    adapter = LedgerAdapter(root, executor)
    prop = LLMProposer(editor, audit_dir=root / "editor")
    print(f"executor={executor.model} editor={editor.model} k={args.k}", flush=True)
    result = run_domain(
        "accounting", adapter.tasks(), args.k, adapter=adapter, prop=prop,
        runs_root=adapter.spec.runs_root, library_root=root / "library", modes=("agg",),
    )
    result["truth"] = {t: f"Total: {truth(a):.2f}" for t, a in TASKS.items()}
    result["usage"] = {"executor": executor.usage, "editor": editor.usage}
    (root / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
