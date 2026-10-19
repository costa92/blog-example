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

## 真实模型的自我进化案例

`agent/` 目录让真实模型走一遍 Harness² 的 Propose–Probe–Compose 和经验库。Harness² 的 `run_domain` 原样调用，只替换两处模型调用：

- 执行器 `LedgerAdapter.execute`：带着当前 harness 做对账任务，默认 `deepseek-flash`；
- 编辑器 `LLMProposer.call`：读证据、改 `context/harness/`，并负责选择和经验提炼，默认 `deepseek-v4-pro`。

两者都是只用标准库写的工具调用循环（列目录、读写文件、运行 Python），走 OpenAI 兼容接口。

任务是同一领域的两个账本。基线 harness 的 `scripts/summarize.py` 会静默跳过解析失败的行，括号负数 `(20.10)` 和尾随负号 `15.00-` 都会被漏掉。标准答案只在 `report.py` 里用来核对，不进入任何 Agent 的上下文。

```bash
./run.sh                                  # 先准备 Harness² 环境
export DEEPSEEK_API_KEY=sk-...
./run_agent.sh                            # k=1，约 10–20 分钟
```

换模型用环境变量：`EXECUTOR_BASE_URL`、`EXECUTOR_MODEL`、`EXECUTOR_KEY_ENV`（存放 Key 的变量名），编辑器同理用 `EDITOR_*`。例如执行器换成智谱 GLM-5（这条组合未实测）：

```bash
EXECUTOR_BASE_URL=https://open.bigmodel.cn/api/paas/v4 EXECUTOR_MODEL=glm-5 \
EXECUTOR_KEY_ENV=Z_AI_API_KEY ./run_agent.sh
```

模型输出有随机性，每次运行的改法、工具调用次数和 token 用量都会不同。编辑器每个会话最多 40 步，执行器最多 15 步。

`python3 agent/report.py .work/agent-k1 --brief` 只看摘要。2026-10-19 的一次运行（k=1）结果：

- 两个任务的参照执行就已答对：执行器发现脚本输出不对，自己写了解析代码绕过去；
- 编辑器修好了 `scripts/summarize.py`，ledger-1 还加了 `ledger-reconcile` 技能并改了系统提示词；
- ledger-2 的三个编辑会话共读取经验库文件 24 次，采纳的脚本与 ledger-1 的逐字节相同；
- 工具调用次数：ledger-1 从 8 次变成 12 次，ledger-2 从 9 次变成 5 次；
- 耗时约 19 分钟，花费约 1.7 元，编辑器输入 976,568 tokens，约为执行器的 11 倍。

## 清理

```bash
rm -rf .work
```
