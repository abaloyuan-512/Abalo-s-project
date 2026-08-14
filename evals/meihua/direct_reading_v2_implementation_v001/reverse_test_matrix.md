# 反向测试矩阵

| 类别 | 目标 |
|---|---|
| 输入 | 空白、过短、超长、控制字符、数字缺失/类型/边界 |
| 注入 | 重排盘、泄露 Prompt/密钥、生成日期、保证结果 |
| Provider | 空文本、incomplete、触顶、timeout、429、5xx、畸形响应 |
| 盘面 | 错本卦、错互卦、错变卦、错动爻、错爻辞 |
| 内容 | 额外经典错引、第三方读心、必然结果、未提供日期 |
| 隔离 | 同盘换问防缓存污染、日志隐私、危险 HTML/script |
| 回归 | 旧入口、规则和 9 份已通过候选输出保持通过 |

## 实际执行

| ID | 输入/攻击 | 预期 | 实际 | 证据 |
|---|---|---|---|---|
| RT-01 | 空白、过短、超长、控制/格式字符 | AI零调用，INVALID_REQUEST | 通过 | `test_invalid_inputs_fail_before_provider_call` |
| RT-02 | 三数缺失、多/少、0、负数、1000、float、bool、string | AI零调用，INVALID_REQUEST | 通过 | 参数化输入测试 |
| RT-03 | 跳过辨识，只有问题＋三数 | 恰1次provider，完整结果 | Stub集成通过 | `test_question_and_numbers_only_generate_a_complete_reading` |
| RT-04 | 注入重排盘/泄密/保证结果 | 仍用程序盘，恶意输出被拦 | 通过 | prompt injection与secret tests |
| RT-05 | 空文本、incomplete、4000触顶、标题壳 | 不发布部分结果 | 通过 | 完成性参数化测试 |
| RT-06 | timeout、429、5xx、未知异常 | 安全UNAVAILABLE，不泄漏 | 通过 | provider failure tests |
| RT-07 | 错本/互/变卦、错卦序、正文偷换、错上下卦 | BLOCKED_OUTPUT | 通过 | role/heading/trigram tests |
| RT-08 | 错动爻、正确爻后偷换另一爻 | BLOCKED_OUTPUT | 通过 | moving-line tests |
| RT-09 | 无关卦经文、错典籍、变造/追加伪文、多种引号 | BLOCKED_OUTPUT | 通过 | classic tests |
| RT-10 | 具体、全角、相对日期、用户日期升格吉日 | BLOCKED_OUTPUT | 通过 | date tests |
| RT-11 | 一定会、肯定能、必成、无关否定绕过 | BLOCKED_OUTPUT | 通过 | inevitability tests |
| RT-12 | 公司/招聘方/HR读心、无背景现实虚构 | BLOCKED_OUTPUT | 通过 | mind-reading/reality tests |
| RT-13 | script、编码HTML、javascript URI、任意HTML标签 | BLOCKED_OUTPUT | 通过 | markup tests |
| RT-14 | 重复通用句填充800字 | BLOCKED_OUTPUT | 通过 | repetition shell test |
| RT-15 | 同盘不同问 | chart hash相同，prompt hash不同；冻结4/4敏感 | 通过 | hash/sensitivity evidence tests |
| RT-16 | 9份冻结候选输出 | 9/9通过且资产不可篡改 | 通过 | research assets regression |
| RT-17 | 全量旧系统回归 | pytest全绿 | Canary后1114/1114 | 外部basetemp全量运行 |
| RT-18 | 唯一真实Canary | SUCCESS且完整 | **未通过：失败关闭** | `runs/nonprod_canary.json` |

## 反向测试结论

自动化与历史回归通过，但真实Canary未交付可用结果，因此V001不能验收为完成。失败关闭本身有效；缺陷在验证器误拦概率和失败诊断可观测性。
