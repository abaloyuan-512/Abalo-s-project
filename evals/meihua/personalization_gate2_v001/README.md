# Gate 2 阶段 A/B 离线实验实现

本目录记录观象个性化解读 Gate 2 的阶段 A/B 状态与治理边界。实现代码位于：

```text
src/abalo_iching/personalization_gate2/
```

自动测试位于：

```text
tests/test_personalization_gate2_offline.py
tests/test_personalization_gate2_plan.py
```

## 当前已实现

- 严格的合成现实输入、A/B/C/D分组、卦象Evidence和结构化输出模型；
- `RWxx`现实事实、`EVxx`卦象事实与`ILxx`实验性解释接榫三条来源链；
- 与正式Validator隔离的实验Validator，分别记录硬安全失败与产品质量失败；
- B组`REALITY_ONLY`、C/D组`REALITY_AND_CHART`的来源约束；
- 最终判断签名与用户可见五字段的来源覆盖检查；
- 只允许Fake Provider和零美元费用的阶段A/B预算硬门；
- 单次生成、无自动修复、保留首次原始输出的离线运行器；
- 仓库外证据包写出、UTF-8/LF与SHA-256清单；
- 安全`case_id`与最终解析路径双重检查，阻止证据目录逃逸或写回仓库；
- 首次完整结构化输出的硬安全扫描，以及现实事实文字与唯一`RWxx`的逐字核对；
- 实验Prompt v2、实验Validator v2与Schema v1的运行前版本坐标核验；
- 锁定测试集、疑似敏感输入、仓库内运行证据写入的前置拦截；
- Fake Provider无网络干跑与自动测试。

## 明确未做

- 没有配置或读取API Key；
- 没有调用OpenAI或其他外部模型；
- 没有产生API费用；
- 没有创建、读取或暴露锁定测试集；
- 没有修改正式网站、视觉、V3、确定性排盘、正式Prompt、正式Validator、Release Gate或解释知识审核状态；
- 没有把实验输出装配进正式产品。

## 本地验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_personalization_gate2_plan.py tests\test_personalization_gate2_offline.py
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

阶段 A/B 完成不自动授权真实模型校准调用。下一阶段只能在产品负责人重新明确批准后启动。
