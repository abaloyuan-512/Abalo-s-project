# Gate 2 阶段 C运行与诊断重试失败分析

## 结论

阶段 C已按硬停止规则停止。首次批次没有自动重试，也没有继续运行剩余五次生成；另行授权的单次诊断重试也只发起一次请求，超时后立即停止。

- 运行日期：`2026-07-21`
- 可见合成案例：`G2CAL-001`
- 已完成A组确定性基线：1
- 已尝试B组Responses API生成：1
- C/D组及第二个案例：未运行
- 首次失败代码：`provider_error`
- 底层错误类型：`ValidationError`
- 诊断重试授权：最多1次生成，新增费用硬上限0.35美元
- 诊断重试结果：`timeout`
- 诊断重试调用数：1
- 自动模型修复调用数：0
- 响应ID：未取得
- Token用量：未取得
- 可核实费用：两次尝试均为未知；原始运行摘要中的`0.0`只表示运行器没有取得Usage对象，不能解释为OpenAI账单已确认零费用；0.35美元是诊断重试授权上限，不是已确认支出
- 锁定测试集：未创建、未读取、未暴露
- 正式产品：零修改

仓库外原始证据保存在：

```text
D:\效率软件--Github\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c_v001_20260721
```

仓库外诊断重试证据保存在：

```text
D:\效率软件--Github\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c_diagnostic_retry_20260721
```

## 已确认事实

1. SDK自动重试配置为0，实验运行器没有自动修复调用。
2. Provider只发起了一次生成尝试；硬失败出现后批次立即停止。
3. 首次失败发生在OpenAI SDK/Pydantic结构验证路径，未形成可供实验Validator检查的`Gate2ExperimentOutput`。
4. 原始证据包没有响应ID、Token统计或模型正文。
5. 全仓821项测试在真实运行前通过。
6. 失败后新增的零网络SDK集成测试证明：相同`responses.parse`调用方式、相同Pydantic Schema和Provider装配，在有效模拟Responses API响应下能够正常解析。因此已经排除“基础SDK接法对所有响应都会失败”。
7. 诊断重试脚本的运行清单固定`maximum_generation_calls=1`、`automatic_model_repair_calls=0`和`authorized_spend_usd=0.35`。
8. 诊断重试只发起1次真实请求，并在OpenAI API请求超时后以`PROVIDER_FAILED`停止；没有响应ID、Usage或模型正文。
9. 两个仓库外证据包的输入/运行记录均通过清单SHA-256复核，诊断重试没有覆盖首次失败证据。

## 尚不能确认

- 初版错误包装只保留了异常类型，没有保留字段级详情；现有证据仍不能确认真实返回具体违反了哪个Schema字段。结合零网络SDK集成测试，最可能是该次真实结构化输出未满足严格Schema，但这是基于排除法的推断，不写成已确认事实。
- OpenAI服务端是否已经生成并计费。没有Usage对象，不能从本地证据给出准确美元数。
- 诊断重试超时发生在请求传输、服务端排队、推理还是返回阶段。API没有返回可核验的响应对象，现有证据不足以进一步归因。

## 本轮修复

- 后续Provider将对Pydantic `ValidationError`单独分类为`structured_output_schema_invalid`，保存经过密钥和本地路径脱敏的字段级详情。
- 后续无Usage对象的生成尝试把费用记录为`null/UNKNOWN`，不再误写成已确认的0美元。
- 本轮不重写原始仓库外证据，保留其原始哈希；本文件作为解释性更正说明。
- 诊断重试记录更新后Gate 2定向50项测试、全仓823项测试通过。

## 诊断重试后的状态

- 新增独立入口`scripts/run_personalization_gate2_stage_c_diagnostic_retry.py`，命令行必须同时确认诊断授权、1次调用和0.35美元上限。
- 诊断重试证据使用新目录写入，保留首次失败证据原样不变。
- 诊断重试没有复现字段级Schema错误，而是在取得API响应前超时，因此不能用本次结果确认或否定首次失败的Schema推断。
- 本轮授权已经用尽，不再追加真实模型调用。

## 产品负责人后续提供的账户侧观察

产品负责人随后提供OpenAI账户24小时Usage截图。截图显示1次Responses/Chat Completions请求、约4185个输入Token和恰好6000个输出Token。6000与当时客户端`max_output_tokens=6000`一致，因此“响应耗尽输出额度后未能在120秒内被本地取得”成为当前最强解释。

这项观察不是原始证据包的一部分，截图中也没有响应ID，无法严格证明它与哪一次阶段 C尝试一一对应；因此只记录为账户侧补充证据，不回写或替换原始失败证据。按GPT-5.6 Sol标准价格估算，该条Usage约为0.18至0.21美元，具体值仍取决于缓存明细。

## 下一步边界

本轮只继续完成失败分析、记录修正、离线验证和已授权的提交推送。任何新的真实API调用都属于另一轮校准，必须重新获得明确授权；阶段 D仍未授权。
