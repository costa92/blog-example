# LLM Wiki 起步模板

包含两个教学案例：Kubernetes 探针排障，以及搜索后端决策追踪。事故、项目、日期均为教学设定，不能当作真实生产记录。探针阅读笔记附 Kubernetes 官方链接。

- 配套文章：[LLM Wiki 知识库实战](https://costalong.com/2026/10/15/llm-wiki-practical-cases/)。
- 示例源码：[costa92/blog-example/llm-wiki-starter](https://github.com/costa92/blog-example/tree/master/llm-wiki-starter)。

## 获取示例

```bash
git clone --depth 1 https://github.com/costa92/blog-example.git
cd blog-example/llm-wiki-starter
python3 check_links.py
```

也可以使用文章中的 ZIP 下载包。GitHub 目录用于浏览源码和获取后续更新。

## 阅读

先读 [SCHEMA](SCHEMA.md)，再读 [索引](wiki/index.md)。在编辑器或 Obsidian 中打开整个目录即可，无第三方运行依赖。用于读写的 agent 仍需要其正常的模型访问方式。

## 查询练习

要求 agent 仅根据本目录回答，并附上文件与章节链接：

1. readiness 失败为何不触发重启？
2. 已经确定事故原因是连接池耗尽了吗？
3. 2026-10-09 已确认使用哪个搜索后端？
4. 2026-10-13 是否允许上传私人笔记？
5. 托管搜索是否已完成部署？

验收要点：readiness 不负责触发重启；根因尚不确定；10 月 9 日仍是本地搜索；私人笔记继续留在本地；批准试点不等于部署完成。每条判断需核对 raw 中的原始记录。

## 分阶段练习更新

模板已经包含全部资料与最终示范页面。若要从头练习，可在一个新目录只复制 SCHEMA.md、raw/k8s-probes-reference.md、raw/incident-demo.md、raw/decision-1001.md、raw/proposal-1008.md，创建空的 wiki/index.md 与 wiki/log.md。不要把最终示范页面提供给 agent。

让 agent 根据规则先构建 wiki，再询问“当前已确认使用哪个后端”。随后复制 raw/decision-1012.md 到新目录，要求按范围更新，而不是覆盖全部旧决策。最后与本模板示范页比较。模板给出的是期望示例，不是某个模型运行结果的保证。

## 结构检查

Python 3.9 或更新版本的标准库即可运行：

```bash
python3 check_links.py
```

检查本地 Markdown 链接、显式锚点与简单标题锚点、索引覆盖。不检查外网链接、不解释事实、不判断来源质量或语义矛盾。增添页面后，应同时补充验收问题。
