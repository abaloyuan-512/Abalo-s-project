# 观象 V72 线上闭环补充证据

状态：`VERIFIED`

对应工作包：`WP-G0-01`

## 本地冻结身份

- 分支：`main`
- 完整提交：`12c5f4307b16e97a86cd5f8b13969ef61478f6d7`
- 冻结标签：`guanxiang-p1-p9-v72-frozen-20260817`
- 冻结记录：`docs/governance/guanxiang-p1-p9-v72-formal-freeze-2026-08-17.md`
- 冻结记录中的 Sites 源码提交：`257f00a705391192bc36beb9f2027eda001f0da1`
- 冻结记录中的 Sites 构建摘要：
  `sha256:e740a0688f4135cf1dec292bc60977042ad868a0f076c8833edb3c18a2adf041`

## 线上后端健康证据

核验时间：`2026-08-18 21:09:38 +08:00`

核验地址：`https://abalo-owner-preview-engine.onrender.com/healthz`

结果：HTTP `200 OK`，安全响应头存在，响应为：

```json
{
  "status": "ok",
  "service": "abalo-authoritative-engine",
  "git_commit": "12c5f4307b16",
  "owner_preview_contract": "SITES_OWNER_PREVIEW_CONTRACT_V1",
  "page8_contract": "SITES_PAGE8_READING_V1",
  "prompt_version": "guanxiang_owner_preview_v8_page8_model",
  "validator_version": "guanxiang_owner_preview_validator_v7_page8_model"
}
```

线上报告的短提交 `12c5f4307b16` 与冻结提交前十二位完全一致。由此关闭冻结记录
中“线上健康检查必须回报冻结提交”的待证据项。

## 边界

本证据只证明 V72 后端健康身份与冻结提交一致；不证明 V73 匿名开放、移动端修复
或真实用户公测已经开始。本次核验没有提交密钥、用户问题、出生资料或模型原文，
也没有发起真实模型调用。
