# Gate 2阶段 C.2单次真实后台复测结果

## 结论

产品负责人授权的唯一一次 C.2真实后台复测已经完成并通过，授权现已消费并硬停止。首次原始输出直接通过`Gate2ExperimentOutputV2`与实验Validator，不需要自动修复或第二次生成。

- 案例：公开合成案例`G2CAL-001/B`；
- 模型：`gpt-5.6-sol`；
- 推理强度：`medium`；
- 最大输出Token：10000；
- OpenAI SDK：2.46.0；
- 生成POST：1；
- 同一response ID轮询GET：16；
- 自动SDK重试：0；
- 自动模型修复：0；
- API终态：`completed`；
- 本地结果：`VALIDATED`；
- 输入Token：5826；
- 输出Token：3295；
- 其中推理Token：475；
- 总Token：9121；
- 按API Usage和版本化价格计算费用：0.127980美元；
- 授权费用硬上限：0.50美元；
- 锁定测试集：未创建、未读取、未暴露；
- 正式产品：零修改；
- 阶段 D：未进入。

本次授权已经用尽。后续不得把本次通过自动扩展为其他案例、其他组别、锁定测试集、阶段 D或正式产品集成授权。

## 验收

- 17个后台检查点对应1次创建状态和16次轮询状态；17个检查点SHA-256全部匹配；
- `run_record.json`哈希与案例证据包`manifest.json`匹配；
- 根证据manifest覆盖生成前已有的39个文件，逐文件SHA-256全部匹配；
- 根证据manifest自身SHA-256为`35e5849d7d151a5a77ed435894a48995a128603bf6395ea803cfe52d05c52b81`；
- Schema v2解析无失败，实验Validator硬失败0项、质量失败0项；
- 费用低于0.50美元硬上限；按声明余额与API Usage计算，仍高于7美元保留线。

## 仓库外证据

完整原始证据只保存在以下仓库外目录，不提交Git：

```text
D:\效率工具--GitHub\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c2_retest_20260721
```

仓库只保存本脱敏结论和根证据manifest哈希，不保存response ID或首次原始输出。
