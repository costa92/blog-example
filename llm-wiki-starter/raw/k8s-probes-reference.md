# Kubernetes 探针阅读笔记

资料类型：官方文档阅读笔记，非官方原文快照。
核对日期：2026-10-15。
来源：[Kubernetes probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)。

<a id="behavior"></a>
## 行为

- liveness 探针达到失败阈值后，kubelet 触发对应容器重启。
- readiness 探针失败时，容器继续运行，Pod Ready 条件变为 false。
- 配置 startup 探针后，liveness 和 readiness 要等 startup 成功后才开始。
- 配置不当的 liveness 探针可能导致级联故障。

具体配置与当前版本行为应回到官方文档核对。
