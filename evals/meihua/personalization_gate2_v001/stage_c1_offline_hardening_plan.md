# Gate 2阶段 C.1离线稳定性加固契约

## 目标

阶段 C.1只解决阶段 C同步请求无法取得响应ID、超时后可能盲目重发、Usage与不完整原因丢失的问题。它不改变个性化解读业务契约、实验Prompt v3、实验Validator v2或Schema v1，也不接入正式产品。

## 后台调用状态机

1. 对公开可见合成案例只允许1次POST创建后台响应。
2. POST返回后立即保存响应ID和初始状态。
3. `queued`或`in_progress`只允许按同一响应ID执行GET轮询。
4. `completed`进入结构化解析与实验Validator。
5. `incomplete`保留Usage、推理Token、费用、部分原始输出和`incomplete_reason`后硬停止。
6. `failed`、`cancelled`、未知状态、检查点写入失败或轮询达到上限均硬停止，不创建第二次生成。
7. 进程恢复必须提供已有响应ID，只执行GET；恢复模式的生成调用数必须为0。

## 检查点与证据

- 检查点只写入Git仓库外目录；
- 每次状态观察使用新的顺序文件，不覆盖旧检查点；
- 每个JSON检查点配套独立SHA-256文件；
- 同一检查点目录只允许一个响应ID；
- 最终证据包版本升级为`personalization_gate2_evidence_v2`，新增`api_status`、`incomplete_reason`、`background_mode`和`poll_count`；
- API Key、请求头和完整内部Prompt不进入证据。

## 候选复测参数

| 项目 | 候选值 |
| --- | --- |
| 模型 | `gpt-5.6-sol` |
| 推理强度 | `medium` |
| 最大输出Token | 10000 |
| 后台模式 | `true` |
| `store` | `false`；OpenAI为后台轮询临时保存响应数据 |
| SDK自动重试 | 0 |
| 自动模型修复 | 0 |
| 最大生成POST | 1 |
| 候选预算硬上限 | 0.45美元 |
| 保守预估 | 0.423050美元 |

将`xhigh`降为`medium`，同时把输出上限从6000提高到10000，是基于账户侧观察形成的稳定性候选组合，并不代表正式产品参数已经确定。它同时改变了两个运行参数，因此下一次单次复测只能验证这一组合是否可用，不能分别归因每个参数的贡献；继续沿用同一实验Prompt和Schema，是为了避免再叠加内容契约变化。

## 当前权限边界

- 本轮真实模型调用数：0；
- 本轮API费用：0美元；
- 产品负责人已另行授权最多1次真实生成，新增费用硬上限0.45美元；
- 付费执行入口只允许`G2CAL-001/B`，并要求显式确认调用数、预算、账户余额、预留额和全新仓库外输出目录；
- 锁定测试集和阶段 D保持关闭；
- 正式网站、V3、确定性排盘、正式Prompt、正式Validator、Release Gate和正式解释知识均零修改。

## 单次真实复测结果

- 授权已使用完毕，只创建1次后台响应；
- API终态为`completed`，同一响应ID轮询22次；
- 首次原始输出因8条`REALITY_FACT`携带非空`reality_refs`而未通过既有Schema；
- 输入4185 Token、输出3841 Token（其中推理699）、总计8026 Token；
- 按API Usage计算费用0.136155美元，低于0.45美元硬上限；
- 没有自动重试、自动修复或第二次生成，阶段 D保持关闭。

## 官方依据

- Background mode与同一响应ID轮询：`https://developers.openai.com/api/docs/guides/background`
- `max_output_tokens`包含推理与可见输出、耗尽后返回`incomplete`：`https://developers.openai.com/api/docs/guides/reasoning#allocating-space-for-reasoning`
- GPT-5.6 Sol标准Token价格：`https://developers.openai.com/api/docs/pricing`

## 进入下一次真实复测前的条件

1. Gate 2定向测试和全仓测试全部通过；
2. 产品负责人明确授权1次真实生成和具体费用上限；
3. 运行目录为仓库外尚未使用的新目录；
4. 执行前再次核对官方价格与账户可用余额；
5. 无论结果如何，不自动重试、不自动修复、不进入阶段 D。
