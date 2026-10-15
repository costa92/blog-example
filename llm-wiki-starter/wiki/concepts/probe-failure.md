# 探针失败的判断

最近核对：2026-10-15。范围：Kubernetes 探针规则与 demo-api 教学事故。

## 规则

readiness 失败本身不触发容器重启；liveness 达到失败阈值才会触发相应的容器重启。
依据：[官方行为笔记](../../raw/k8s-probes-reference.md#behavior)。

## 事故判断

demo-api 的 readiness 失败与 restartCount 为 0 可以同时出现。
记录中的数据库连接超时只支持依赖访问异常这一观察，根因尚未确认。
依据：[观察](../../raw/incident-demo.md#observations)与[缺少证据](../../raw/incident-demo.md#gaps)。

## 待评估动作

不要仅为触发重启而将依赖数据库的 readiness 检查改为 liveness。应先判断重启能否恢复服务，以及是否会扩大依赖故障的影响。这是基于探针语义与案例材料的分析，未形成已执行变更。
依据：[官方行为笔记](../../raw/k8s-probes-reference.md#behavior)与[未执行建议](../../raw/incident-demo.md#suggestion)。

来源归纳见[来源页](../sources/probes-and-incident.md)。
