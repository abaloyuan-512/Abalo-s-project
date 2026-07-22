# Gate 2阶段 C.3可见卦象组真实后台运行结果

## 结论

产品负责人授权的唯一一次 C.3真实后台运行已经完成，授权现已消费并硬停止。公开合成案例`G2CAL-001`按固定顺序先运行C组、后运行D组；两组首次原始输出均直接通过`Gate2ExperimentOutputV2`与实验Validator。

当前工程状态为`READY_FOR_BLIND_REVIEW`。这只表示B/C/D公开可见链路已经具备盲评输入，不等于Gate 2、产品价值、锁定测试集或阶段 D通过。

## 授权与运行坐标

- 声明余额：8.57美元；
- 总费用硬上限：1.00美元；
- 要求保留余额：至少7.00美元；
- 案例：公开合成案例`G2CAL-001`；
- 顺序：先C、后D；
- 模型：`gpt-5.6-sol`；
- 推理强度：`medium`；
- 最大输出Token：10000；
- OpenAI SDK：2.46.0；
- Schema：`gate2_schema_v2`；
- Prompt：`personalization_gate2_calibration_v4`；
- Validator：`personalization_gate2_validator_v3`；
- `background=true`、`store=false`、`tools=[]`；
- 自动SDK重试：0；
- 自动模型修复：0；
- 失败补发：0。

运行前保守预检为：C组0.475313美元、D组0.475307美元，合计0.950620美元，低于1.00美元硬上限。

## 脱敏结果

| 组别 | 生成POST | 同一ID轮询 | API终态 | 本地结果 | 输入Token | 输出Token | 推理Token | 总Token | 费用 |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| C | 1 | 19 | `completed` | `VALIDATED` | 6139 | 6523 | 1059 | 12662 | 0.226385美元 |
| D | 1 | 19 | `completed` | `VALIDATED` | 6136 | 4600 | 754 | 10736 | 0.168680美元 |

两组总费用为0.395065美元。按声明余额扣除本次Usage计算，剩余8.174935美元，高于7美元保留线。两组Schema硬失败、Validator硬失败和质量失败均为0。

## 证据验收

完整原始证据只保存在以下仓库外目录，不提交Git：

```text
D:\效率软件--Github\文件储存夹\Abalo-s-project-eval-output\gate2_personalization_stage_c3_visible_chart_arms_20260722
```

- 根证据清单覆盖88个文件；
- 88个文件SHA-256全部重新计算并匹配；
- 根证据清单自身SHA-256为`32815df7c65702a6c071d7418bdeb81932aaa13678855e41ecedf03e296783d2`；
- 仓库不保存response ID、首次原始输出、API Key或完整敏感内容。
- 运行前Gate 2定向133项、全仓906项通过；收口新增1条结果治理测试后，Gate 2定向134项、全仓907项通过。

## 继续关闭的边界

- 锁定测试集未创建、未读取、未暴露；
- 阶段 D未进入且未授权；
- 正式网站、V3、确定性排盘、正式Prompt、正式Validator、Release Gate和正式解释知识均未修改；
- C.3付费入口已消费，不得再次生成或补发；
- 下一步仅可组织至少3名互相独立的评审，在不知道组别的情况下使用冻结Rubric评审B/C/D输出。任何锁定集、阶段 D或正式产品动作仍需新的独立批准。
