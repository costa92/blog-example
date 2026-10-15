# demo-api 探针异常

资料类型：虚构教学事故记录。
时间：2026-10-06 10:20 至 10:32。

<a id="observations"></a>
## 观察

- Pod 为 Running，READY 为 0/1，restartCount 为 0。
- 事件出现 Readiness probe failed。
- /readyz 的检查包括数据库连接，应用日志出现连接超时。

<a id="gaps"></a>
## 缺少证据

没有当时的数据库连接数、连接池指标、网络连通性记录，以及发布前后的配置差异。

<a id="suggestion"></a>
## 尚未执行的建议

有人建议把 readiness 换成 liveness，让异常时自动重启。建议尚未评估，也未执行。
