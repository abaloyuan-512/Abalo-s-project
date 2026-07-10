# Meihua Engine Phase 1 Acceptance

状态：Phase 1 自动化验收通过。

## 验收命令

```powershell
.\.venv\Scripts\python.exe -m compileall src tests scripts
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=src/abalo_iching --cov-report=term-missing
.\.venv\Scripts\python.exe scripts\verify_wheel_install.py
.\.venv\Scripts\python.exe scripts\demo_meihua_engine.py
```

## 固定金标准

Fixture 为 `tests/fixtures/golden_cases_v1.json`。前四例固定为 1/1/1、8/8/6、999/999/999、100/27/368；另有不少于 16 个手工案例覆盖六个动爻、五种关系、余数零、输入边界、纯阳纯阴、不同互卦和变卦。

## 完成项

- 规则与数据契约
- 八卦与 64 卦版本化静态数据
- 确定性本卦、互卦、变卦、体用、关系、历法、旺衰、证据和 JSON 引擎
- 自动化测试与演示脚本

## 未完成/后续阶段

- 旧版 Streamlit/CLI 入口迁移
- AI 解释层与报告
- 具体日期应期
- 用户、数据库、付费等产品能力

## 最终结果

- 测试数量：142
- 覆盖率：95%（`src/abalo_iching`）
- compileall：通过
- pytest：142 passed
- 普通 wheel 干净安装：`scripts/verify_wheel_install.py` 通过
- 演示：100/27/368 得第55卦雷火丰、二爻、互卦第28卦泽风大过、变卦第34卦雷天大壮；小暑未月；JSON 输出成功
