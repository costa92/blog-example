"""给 inv1、dom1 两个候选打分。harness2-judge 只评采纳版和参照执行，候选要直接调适配器的 score()。"""

import shutil
import sys

from harness2 import config
from harness2.cli import _common as C


def main() -> int:
    domain = sys.argv[1]
    task = f"{domain}/task1"
    config.validate_models(judge=True)
    adapter = C.make_adapter("jb", None, "oc")
    task_dir = config.RUNS / "jb" / "dataset" / task
    for label in ("inv1", "dom1"):
        name = f"jb-oc-agg1__{domain}__task1__{label}"
        # 裁判结果按运行缓存，删掉才会重新调用模型。
        shutil.rmtree(task_dir / "eval_result" / f"eval_{name}", ignore_errors=True)
        got = adapter.score(task_dir / "model_output" / name, task)
        shown = "judge failed" if got is None else f"{got['n_passed']}/{got['n_criteria']}"
        print(f"  {task:<52} {label} {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
