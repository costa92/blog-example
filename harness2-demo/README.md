# Harness² 离线 demo 复现

复现谷歌开源的 [Harness²](https://github.com/google-research/harness2) 自带离线 demo，并对文章里的实测结论逐条做断言。demo 的编辑器和选择器是 Harness² 仓库里写死的脚本，不调用任何模型，不需要凭证。

- 配套文章：DeepSeek 跑 Harness²：一步从 6.8% 到 27.3%。
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

## 用 DeepSeek 跑 JobBench，对照论文

论文的 GLM-5 数据来自 Vertex AI 上的模型。WorkBuddy-Bench 的安装脚本只接 Vertex Gemini，JobBench 允许另配裁判接口，所以这里用 Harness² 自带的 JobBench 适配器，执行器 `deepseek-flash`，编辑器和裁判 `deepseek-v4-pro`，k=1 并行模式，只跑一个领域的第一道题。

```bash
./run.sh                                  # 先准备 Harness² 环境
export DEEPSEEK_API_KEY=sk-...
./run_jobbench.sh                         # 默认簿记审计领域；DOMAIN=<领域名> 可换
```

首次运行会执行 `harness2-setup jb`，从源码构建固定版本的 OpenCode 并下载 JobBench 数据集（65 道题）。脚本把 `HOME` 和 OpenCode 配置目录指到 `.work/` 下的独立目录，避免加载本机的插件和技能，并关闭 webfetch 与 websearch。这挡不住执行器用 curl 联网，要防评分标准泄漏，需要在网络层封掉 `huggingface.co` 等域名。

`harness2-judge` 只评采纳版和参照执行，`jobbench/judge_candidates.py` 补评 inv1、dom1 两个候选。裁判结果按运行缓存在 `eval_result/`，删掉才会重新调用模型。

2026-10-20 簿记审计 task1 的结果（加权分，满分 88）：

| 执行 | 各次评分 |
|---|---|
| base1（参照执行） | 6、6 |
| inv1 | 34、52、34 |
| dom1 | 24、24、14 |
| agg1（采纳） | 24、24 |

- 参照执行 6.8% → 采纳版 27.3%；论文 GLM-5 · OpenCode 为 20.6 → 24.2（34 题 × 3 次，编辑器与裁判为 Opus 4.8），单题单次只能比方向；
- 参照执行编造了 AP 明细账，inv1 用搜索引擎从 excelx.com 下载了真实文件，编辑器却把 inv1 的数据记成编造，合成版没有去取文件；
- 一步改进约 10.4 元（参照执行 20 分钟、两个候选并行 12 分钟、合成版 9 分钟），裁判每评一次约 0.9 元。

## 清理

```bash
rm -rf .work
```
