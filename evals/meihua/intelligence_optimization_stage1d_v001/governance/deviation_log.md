# 阶段1D偏差记录

| ID | 原计划 | 当前实际 | 原因 | 影响 | 纠正动作 | 是否需用户确认 |
| --- | --- | --- | --- | --- | --- | --- |

| S1D-DEV-001 | 冻结保护集应与合同维度枚举兼容 | 首次冻结后结构预检发现`expected_dimension`使用更细的独立命名空间 | 保护集与合同在封存前只共享语义目标，未共享枚举协议 | 正式运行无法通过前置校验；当时0模型调用、0正式运行、无marker，Prompt/合同/runner均未修改 | PMO批准一次全局无歧义机械映射；保留原文件及旧hash，新建v2且验证除`expected_dimension`外零变化 | 否；属于获批范围内的冻结兼容校正 |
| S1D-DEV-002 | 冻结前应证明实际发送的wire schema被目标服务端接受 | 只验证了SDK能生成strict schema和本地Pydantic可解析，没有进行真实服务端canary | 把合法JSON Schema误当成目标Structured Outputs受限方言的兼容证明 | 唯一run 10/10在推理前400，能力问题完全未观测 | 本阶段不修补或重跑；验收定为INVALID；新阶段必须先做Critic与Proposer canary | 若继续需用户授权新阶段 |
| S1D-DEV-003 | 全局不可恢复错误应立即停止 | 首个`invalid_json_schema`后runner继续遍历其余9案 | 错误分类只区分transport/parse，未识别全局Schema negotiation失败 | 产生9次必然失败的API请求；0 token、非重试，但浪费调用并污染诊断噪声 | 如实记录；新runner需分类`SCHEMA_COMPATIBILITY_ERROR`并全局短路 | 否，本阶段关闭 |
