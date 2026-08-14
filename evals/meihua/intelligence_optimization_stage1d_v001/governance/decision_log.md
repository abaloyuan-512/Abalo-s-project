# 阶段1D决策日志

| ID | 决策 | 依据 | 影响 |
| --- | --- | --- | --- |
| S1D-DEC-001 | Critic先于Proposer且看不到Proposer | 阶段1C的M02显示审查器会被完整提议锚定 | VETO路径不再产生无效Proposer调用 |
| S1D-DEC-002 | 证据值采用可判别互斥联合类型 | 阶段1C三次出现非GROUNDED状态携带内容 | 非法组合在解析层失败并可被精确定位 |
| S1D-DEC-003 | 失败调用与成功调用同等留痕 | 阶段1C失败调用缺少原始输出与usage | 调用数、成本和合同失败可完整审计 |
| S1D-DEC-004 | 不设临时成本通过阈值 | 当前首要问题是能力是否成立 | 记录并比较成本，不用事后阈值改变结论 |
| S1D-DEC-005 | 使用`responses.create`后手工合同解析 | 阶段1C和初版1D的`parse`会在Schema错误时丢失原始响应与usage | HTTP成功但合同失败仍可保存response id、raw JSON、usage、延迟和字段错误 |
| S1D-DEC-006 | 保护集只验证首次分类 | 已批准README与PMO闸门要求保护集6/6首次分类；回答后4/4收束只属于核心集 | 不把封存回答追加为新的保护集通过条件，避免冻结前扩大范围 |
| S1D-DEC-007 | `all_mechanical_gates_pass`不代表价值通过 | 粗粒度dimension不能证明M02/M04语义命中 | 正式运行后仍由PMO逐案审查definition、question、evidence与proposal |
| S1D-DEC-008 | 运行锁使用排他创建 | 检查后普通写入存在并发竞态 | 首个进程原子取得marker，其他进程在任何模型调用前失败 |
| S1D-DEC-009 | 允许一次保护集命名空间兼容修订 | 首次预检在0调用、无marker时发现全局标签与冻结四值枚举不兼容；PMO认定不涉及案例内容或模型表现 | 保留v1谱系；独立代理生成v2，仅机械修改`expected_dimension`；第二次预检失败则停止 |
| S1D-DEC-010 | 唯一run归类为INVALID而非FAIL | 10/10请求在模型推理前被相同服务端Schema错误拒绝，0 token、0语义输出 | 不能据此支持或否定Critic-first能力，只能证明wire schema不可执行 |
| S1D-DEC-011 | 不修补后重跑阶段1D | 正式marker和保护集已经消耗，冻结纪律禁止修正后派生通过版 | 阶段1D关闭；任何继续必须新阶段、新保护集和新授权 |
| S1D-DEC-012 | H11—H16永久退出保护用途 | run文件已经包含案例正文、预期标签和维度 | 后续有效实验不得复用这些案例作为heldout |
