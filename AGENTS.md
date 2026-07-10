# Abalo-s-project Engineering Rules

1. 术数规则以 `docs/specs/` 中的版本化规范为准。
2. 不得在没有升级规则版本时改变算法。
3. AI 不得参与确定性排盘。
4. 程序没有提供日期时，AI 不得生成日期。
5. 不得把现实背景伪装成卦象证据。
6. 现有旧版入口在完成迁移验收前不得删除。
7. 所有引擎修改必须通过 `pytest`。
8. 不得提交密钥、验证码、用户出生资料。
9. 新模块必须采用明确的数据模型和类型标注。
10. 不得通过“看起来合理”代替测试。

## Phase 1 boundaries

- 确定性引擎只能依赖版本化规则和静态数据。
- `lunar_python` 只能由 `calendar_provider.py` 适配。
- Phase 1 不输出具体日期、吉凶总评或领域建议。
- `streamlit_app.py` 与 `iching_tools.py` 是迁移前旧版入口，不得在 Phase 1 修改。
