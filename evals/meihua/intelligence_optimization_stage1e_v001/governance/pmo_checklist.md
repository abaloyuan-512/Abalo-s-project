# 阶段1E PMO检查表

## 范围

- [x] 已获得阶段1E明确授权。
- [x] 只修wire schema兼容、canary和后续能力验证基础设施。
- [x] 未修改生产、UI、API、数据库、排盘、解卦或知识库。
- [x] 未进入阶段2。

## Canary硬门

- [x] Critic/Proposer实际wire schema不含`oneOf/discriminator`。
- [x] 扁平字段由后置validator强制互斥。
- [x] Critic ASK canary通过。
- [x] Critic READY canary通过。
- [x] Proposer canary通过。
- [x] 首个Schema兼容错误可全局短路。
- [x] Canary前Prompt、合同、Schema与runner哈希冻结。
- [x] 专项测试和canary前完整回归通过（22专项；1024完整）。

## 正式能力闸门

- [x] Canary全过后才生成全新6案保护集（现已放行生成，尚未完成冻结）。
- [ ] M01—M04首次4/4 ASK、回答后4/4 READY并形成瓶颈。
- [ ] 新保护集首次6/6正确且语义命中。
- [ ] 唯一正式run、零重试、完整调用对账。
- [ ] 完整回归通过且生产零变更。

## 阶段闸门

- [ ] 阶段1E能力问题得到有效验证。
- [ ] 用户确认是否进入任何下一阶段。

PMO状态：`CANARY_PASSED_HELDOUT_GENERATION_AUTHORIZED`。
