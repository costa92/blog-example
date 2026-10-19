# Harness² 离线 demo 复现

复现谷歌开源的 [Harness²](https://github.com/google-research/harness2) 自带离线 demo，并对文章里的实测结论逐条做断言。demo 的编辑器和选择器是 Harness² 仓库里写死的脚本，不调用任何模型，不需要凭证。

- 配套文章：谷歌开源 Harness²：不碰模型权重，GLM-5 一轮涨 11.5 分。
- 示例源码：[costa92/blog-example/harness2-demo](https://github.com/costa92/blog-example/tree/master/harness2-demo)。
- Harness² 固定在 commit `1cfe254e8d25b15f37048c3730134686abe60335`（版本 `0.1.0`）。

## 运行

需要 Linux、git 和 [uv](https://docs.astral.sh/uv/)。uv 会自动准备 Python 3.12。

```bash
git clone --depth 1 https://github.com/costa92/blog-example.git
cd blog-example/harness2-demo
./run.sh
```

首次运行会把 Harness² 克隆到 `.work/harness2` 并建虚拟环境，之后重复运行直接复用。输出末行为 `全部断言通过` 即复现成功。

## 校验内容

`check_demo.py` 只用标准库，分四步：

1. k=1 并行模式：ledger-1 的参照执行得 `Total: 105.25`，两个候选和合成版都得 `Total: 85.15`；两个任务共执行 8 次、调用编辑器 8 次。
2. 被采纳的 `scripts/summarize.py` 删掉了 `if amount > 0`。
3. EXPERIENCE.md 含 cue、lesson、evidence 三项，k=1 时没有调用选择器。
4. k=2 两种模式共执行 28 次、调用编辑器 32 次；ledger-2 开始前两个经验库各有 1 条。

断言只覆盖 demo 的流程与计数，不代表真实模型的改进效果。真实基准（JobBench、LAB、WorkBuddy-Bench）需要 Vertex AI 等环境，见 Harness² 的 README。

## 清理

```bash
rm -rf .work
```
