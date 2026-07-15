# Sites Meihua API Contract V2

V2 仅接受有限结构化字段，并由服务端使用
`SITES_STRUCTURED_QUESTION_TEMPLATE_V1` 生成唯一规范化问题。

## Endpoint

`POST /api/v2/meihua`

## 安全边界

- 请求不得包含 `question_text`、`normalized_question`、背景文本、卦象、Evidence、结论或任何客户端派生结果。
- 只有 `request.schema.json` 中的字段可提交；未知字段默认拒绝。
- 领域与目标必须出现在服务端的有限允许组合表中。
- `client_timestamp` 仅供审计，不决定排盘时间。
- Narrative 继续为 `UNVERIFIED`；Release Gate 与 V1 相同。
- V1 contract 与 `POST /api/v1/meihua` 保持原样。

`sample_request.json` 是合法请求，`sample_success_response.json` 和
`sample_validation_error.json` 分别展示成功与安全验证错误 envelope。
