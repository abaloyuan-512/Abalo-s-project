# Design QA — 第三页「正问」顶部云层横向修正版 v11（2026-08-01）

## 对照依据

- 用户截图：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-a9659138-81ce-4f4d-867a-aee0669a165a.png`。
- 实现帧：`qa/inquiry-cloud-horizontal-v11-final-t1.png`、`qa/inquiry-cloud-horizontal-v11-final-t2.png`。
- 动态差异与组合对照：`qa/inquiry-cloud-horizontal-v11-final-diff-x8.png`、`qa/inquiry-cloud-horizontal-v11-final-comparison.png`。
- 验证环境：1280 × 720 CSS viewport，DevicePixelRatio 1.25。

## 修正结果

- 顶部云层只沿水平方向轻微往复；关键帧的 Y 位移固定为 0，纵向缩放固定为 1，不再产生上下漂浮或呼吸式升降。
- 顶部动态云层增加硬边界裁切，只覆盖左上至中部云区，不再包含右侧山峰。
- 两个最终帧的右上山峰区域逐像素差为 0；山体本身保持静止。
- 顶部云区平均通道差约 3.55–3.90，肉眼可感知但幅度接近松树的舒缓节奏。
- 前景流云、松树和页面排版保持原有实现，不受本次顶部云层修正影响。

## Comparison History

1. v10：透明度和缩放变化可见，但纵向缩放与位移造成云层上下运动的错觉，且局部遮罩仍纳入山峰。
2. v11：改为纯 X 轴位移，锁定 `scaleY(1)` 与 Y=0；使用多边形裁切排除山峰区域。

## 工程验证

- Vinext production build：passed。
- Node rendered/interaction tests：28 / 28 passed。
- ESLint：0 errors；14 个既有 warnings。
- `git diff --check`：passed。

final result: passed

---

# Design QA — 第三页「正问」可见云海动效 v7（2026-08-01）

## 对照依据

- source visual truth：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-9d06dc28-1b60-48dd-88e6-d5a72a32d191.png`（用户指定的左上云海区域），以及此前选定的第二张云瀑概念图 `C:\Users\27622\.codex\generated_images\019fa5e9-2a61-7f92-813b-b9d609ccb12c\exec-04c25898-61ae-4837-92eb-6bbe9106ac01.png`。
- implementation screenshots：`qa/inquiry-cloudfall-v7-motion-iab-t1.png`、`qa/inquiry-cloudfall-v7-motion-iab-t2.png`，相隔 1.7 秒。
- full-view comparison：`qa/inquiry-cloudfall-v7-full-comparison.png`。
- focused comparison：`qa/inquiry-cloudfall-v7-focused-comparison.png`。
- motion evidence：`qa/inquiry-cloudfall-v7-motion-diff.png`。
- 浏览器状态：Codex in-app Browser；CSS viewport 1280 × 720；devicePixelRatio 1.25；截图传输像素 1265 × 712；`#inquiry`；问题为空。
- 归一化：focused comparison 将用户截图和浏览器截图中的顶部云海区域等比裁切并统一到 1265px 宽；full-view comparison 将概念图与实现等比统一到 632 × 356。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 用户提出的第五页落霞动效方法已部分采纳：第三页新增基于同一真实水墨底板的两个软边局部重采样层，只作用于左上迎风云海与峰顶云脊；通过背景位置、缩放、轻微形变与明暗起伏形成肉眼可见的连续推进，不复制第五页的红霞颜色和具体轨迹。
- 原有两层 WebGL 云继续负责峰顶分流、宽瀑与窄瀑的下泄；速度、明暗跨度、内部脉动和阴影对比均已增强。没有平铺、首尾拼接、硬边图片或三角形接缝。
- 相隔 1.7 秒的两帧中，左上云海区域亮度差大于 5 的像素占 56.97%，大于 10 的像素占 26.79%；峰顶与下泄云瀑区域对应比例为 21.72% 和 9.69%。变化已达到肉眼可辨，同时没有把整张背景作为一个图层平移。

## Required Fidelity Surfaces

- Fonts and typography：书法标题、楷体输入、例句与导航字号、字重、行距和字间距未改变；动画层始终位于正文后方。
- Spacing and layout rhythm：用户截图中的顶部云海、标题、问题输入关系保持不变；背景满框，未引入新的卡片、边界或布局位移。
- Colors and visual tokens：沿用宣纸米白、淡墨与朱砂；云层仅调整亮度与墨色对比，没有引入第五页的红霞色。
- Image quality and asset fidelity：继续使用 `question-cloudfall-base-v6.png`、`question-cloudfall-mountain-v5.png` 和独立松树真实位图；新增层只是对真实底板的软边局部重采样，未使用占位图、SVG 或代码绘画替代水墨资产。
- Copy and content：页面文字、四个例句、输入提示与按钮文案均未改变。

## Interaction And Engineering Verification

- 输入“我是否应该继续投入这次合作？”后，“写好了，继续辨识”按钮可用；清空后恢复原状态。
- 浏览器 console errors：0；两个 WebGL canvas 和一个局部云海重采样层均存在并可见。
- `prefers-reduced-motion` 下新增重采样层停止动画，现有 WebGL 固定为静态时刻。
- Vinext production build：passed。
- Node rendered/interaction tests：28 / 28 passed。
- ESLint：0 errors；14 个既有 `<img>` / ARIA warnings。
- `git diff --check`：passed。

## Comparison History

1. v6：两层 WebGL 实际运行，但静态云海底板占主导；用户和浏览器连续观察均只能明显看到松树，云层肉眼几乎不可辨，判定为 P1。
2. v7 iteration 1：引入第五页落霞的软边局部重采样方法并提高 WebGL 速度与不透明度；顶部云海已明显变化，但峰顶下泄仍偏弱。
3. v7 final：继续提高下泄云瀑的连续体密度、细节明暗和阴影跨度；1.7 秒两帧在顶部与下泄区域均达到可辨变化，组合对照未发现重影、硬边或接缝。

## Follow-up Polish

- 仅保留用户主观速度偏好的微调空间；当前无阻断项。

final result: passed

---

# Design QA — 第 4–5 页结束状态与问数节奏修复 v4

## 用户反馈与根因

- 回答完第 8 问后，前端把“达到硬上限”与“用户主动提前结束”合并成同一个 `STOPPED` 状态，因此错误显示“你选择了提前结束”。
- 旧提示把 4–7 问写成常规区间，却没有明确要求“信息足够立即完成”，容易让引导者为了覆盖固定字段继续追问。
- 第 5 页和基础引导的说明直接露出“AI”字样，破坏整体语言质感；提前结束、自然问清、达到八问三条路径也缺少独立文案。

## 已落实

1. 新增 `ENOUGH / MAX_TURNS / USER_EARLY` 三种完成原因。第 8 个回答后即使上游仍返回 `ASK`，也会保留该轮的结构化整理与题目建议并进入正常判断，不再进入“主动提前结束”分支。
2. 引导规则改为“信息足够立即完成，不得为了达到固定题数继续追问”；常规目标收紧为 4–6 问，8 问只作为防止无休止追问的硬上限，与用户主动结束无关。
3. 需要换题时保留用户指定的建议句式和“采取建议／保持原题”；用户选择后以“那现在……”承接。无需换题或提前问清时直接显示“现在已经更清晰……”。
4. 只有用户主动提前结束时显示：“我感受到你想尽快进入取数卜卦的环节，现在请心中再次默念你的问题，深呼吸。”
5. 删除页面可见的“AI 改写建议”“回答 AI 当前问题”等表述；服务错误改为明确但中性的“辨识服务暂时未连接／连接超时”。
6. 提前结束的过渡页删除“已经整理到这里／不必为了问完”等解释，以《周易·系辞下》“穷则变，变则通，通则久”替代，并保留单一“继续定问”动作。

## 工程验证

- `vinext build`：通过。
- 前端测试：25 / 25 通过，新增三种完成原因、八问正常收束、提前结束专属文案与经典引文约束。
- ESLint：0 error；5 个既有 warning，没有新增 warning。
- 全量 `pytest`：946 / 946 通过。首次将临时目录放在仓库内时，21 个真实评测安全测试按设计拒绝仓库内证据目录；改用系统临时目录后全绿。
- `git diff --check`：通过。
- 本地浏览器预览进程在当前桌面运行环境返回 500，未以静态截图替代真实交互验证；发布后继续在实际站点检查桌面与手机断点。

---

# Design QA — 第 4–5 页等待、恢复与定问简化 v3

## 用户反馈与根因

- 第 4 页左侧说明改为用户指定文案：“为了能结合卦象，给你更具实际意义的建议，我还有几个问题请你回答。”
- 旧流程进入辨识后先显示“开始 AI 辨识”按钮；点击后首问完全依赖一次上游调用，因此冷启动时页面没有问题，只剩“正在静心听你所问”。
- 旧流程任一轮请求失败都会回到 `READY`；页面上的“重新连接 AI 辨识”实际调用全量 `start()`，清空 `turns`、草稿和本次整理结果，因此用户必须从第一题重答。
- 前端转发层按 UTF-8 字节限制为 16KiB，但 Python 辨识传输与会话约束允许约 32KiB。中文通常占三字节，后期轮次会比英文更早被前端拒绝。
- 旧第 5 页重复展示原题、AI 建议与“最终问卦题目”编辑区，信息量超过用户此时真正需要做的决策。

## 已落实

1. 进入第 4 页即刻呈现固定的基础首问“这件事现在具体走到了哪一步？”，不再用一次 AI 请求换取首问，也不再出现“开始 AI 辨识”按钮。该首问明确属于产品流程；从用户第一句回答之后，下一问才由 AI 根据已给上下文动态承接。
2. AI 整理期间保留用户刚刚回答的内容，显示“你刚才的回答已经记下”及当前处理目标；页面不再出现无问题的空白等待，也不使用“正在聆听”类模糊文案。
3. 请求失败时保留 `sessionId`、全部 `turns` 和本轮待重试上下文。页面明确显示“前 N 个回答都还在”，点击“继续这一轮”只重试失败请求，不清空、不重复提交前面的问题；基础引导仍需用户主动选择。
4. 修正前端转发错误优先级：先处理上游非成功状态，再验证成功响应的会话 ID，避免把真实的服务暂不可用误报为“返回异常”。同时把请求上限与 Python 传输对齐为 32KiB，新增五轮长中文回答回归用例。
5. 第 5 页不再呈现原题卡片、原题全文、“最终问卦题目”编辑区或字符计数。
6. AI 建议与原题实质相同时，直接呈现：“现在已经更清晰你的现状，我们准备开始取数卜卦了。请心中再次默念你的问题，深呼吸。”
7. AI 确实建议换题时，只呈现建议题目、建议理由和“采取建议／保持原题”两个按钮；用户选择后才进入同一段默念与呼吸提示。AI 不会替用户确认最终题目。
8. 定问页中下部复用首页的朱砂细线式按钮语言，设置居中的“开始卜卦”；点击后才解除第 6 页门控并滚动至取数页。

## 实际浏览器检查

- 桌面本地流程：进入第 4 页后第 1 问与回答框即时出现，没有首问按钮或空白等待。
- 断线恢复：在本地未连接 AI 上游的真实失败路径中，回答第一问后页面显示“前 1 个回答都还在”，并提供“继续这一轮”；没有“重新连接 AI 辨识”，已有回答未清空。
- 原题不改分支：主动进入基础引导并提前结束后，第 5 页只显示准备语、默念呼吸提示和居中“开始卜卦”，页面没有再次显示原题，也没有最终题目编辑板块。
- 桌面截图检查：第 5 页标题、准备语、重点呼吸提示与开始按钮完整落在 1280 × 720 首屏，无横向拥挤。
- AI 换题分支通过组件条件、按钮回调和题目写回逻辑审计；本地上游未连接，因此未伪造 AI 返回进行视觉冒充。

## 工程验证

- `vinext build`：通过。
- 前端测试：25 / 25 通过，含长中文多轮请求与恢复交互静态约束。
- ESLint：0 error；5 个既有 warning。
- 全量 `pytest`：首轮旧临时目录权限冲突；新临时目录运行 944 / 945，通过后唯一 Windows socket 瞬时中止用例单独复跑通过。与本轮相关的辨识、托管 API 和 Sites 测试全部通过。
- `git diff --check`：通过。
- 未修改确定性排盘算法、规则版本或旧版入口；AI 仍不参与排盘，也未把现实背景当作卦象证据。

final result: passed

---

# Design QA — 第 7 页「观卦」太极水墨与双锦鲤动效

- Source visual truth：用户确认的中间值太极背景方案。
- 第 7 页仅呈现卦象、卦序、卦名、卦辞和“详细解卦”；不呈现用户原问题，不提前展开后续解释。
- 太极图为独立宣纸背景；两条透明锦鲤分别以独立目标、速度、转向和相位运行。
- 鱼身沿脊线分片弯曲，尾部摆幅大于头部，不是固定图片整体平移。
- `prefers-reduced-motion` 下停止持续游动，窗口尺寸变化后重新绘制静态构图。
- 桌面浏览器已验证两条鱼在连续状态间独立位移、转向；“详细解卦”点击后才显示后续内容。
- 本次部署以线上第 6 页定稿为基底，仅叠加第 7 页实现与直接相关资产。

final result: passed

---

# Design QA — 辨识等待与牡丹成卦 v1

## 比较依据

- 用户问题证据：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-14632635-f1da-4075-84f2-ba2b5c5cf1f4.png`、`C:\Users\27622\AppData\Local\Temp\codex-clipboard-a82f5d69-0701-4323-b3eb-475151cdceda.png`、`C:\Users\27622\AppData\Local\Temp\codex-clipboard-2393c57b-1aec-4136-9faa-025858a95bb2.png`。
- 用户选定的等待视觉：`C:\Users\27622\.codex\generated_images\019fadc2-e346-7343-9859-11ea17af676a\exec-ea67a429-0c2b-4744-85a2-7402575187d4.png`，方案二「山岚过卷」。
- 实现资产：`public/discernment-mist-scroll-v1.png`、`public/casting-peony-background-v1.webp`、三张透明牡丹花层与一张透明花瓣层。
- 实际浏览器检查：桌面 1440 × 900；手机 390 × 844。浏览器截图与上述来源在同一轮检查中并置比较，覆盖辨识首问、服务失败保留回答、提前结束、定问收束、成卦初始花开和落瓣后状态。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 等待状态：旧版单根移动细线已移除。当前为无卡片边缘的淡墨山岚，在说明文字下方被薄雾缓慢揭开并归于纸色；图像四角透明，与宣纸背景连续。状态文字说明正在整理上一句，回答已保存。
- 问数控制：八问只保留为绝对上限，不再作为完成条件。已确认事实与未知项充分时，模型可立即结束；到第六轮仍有扎实上下文时程序主动收束，降低“没完没了”的感受。
- 建议问句：只有 6–160 字、包含中文疑问表达并以问号结尾的完整问句才会进入定问建议。行动清单、岗位安排、名词标题或祈使句全部回退为用户原题，不再把非问题内容展示成换题建议。
- 成卦构图：沿用定问的左侧大字层级，右侧改为整幅枝叶牡丹背景；三朵透明花层按错落位置融入枝干，输入框随花布置，没有矩形图片边缘，也没有与宣纸割裂的底色。
- 动效：三息依次轻微呼吸，花瓣逐片下落、旋转、褪墨，花朵随后透明隐去；背景花托和枝叶仍在，形成花谢而不突兀的连续画面。`prefers-reduced-motion` 下花朵保持完整、花瓣隐藏、等待山岚静止。
- 桌面与手机：1440 × 900 下左题右景层级清楚，三朵牡丹及数字在首屏完整呈现；390 × 844 下转为纵向长卷，大标题、说明、三息与输入均无横向溢出，触屏数字输入保持原生语义。
- 边界：三数仍只交给程序，既定规则继续独立排定本卦、互卦与变卦；本轮没有让 AI 参与确定性排盘，也没有把现实信息写成卦象证据。

## 工程验证

- `vinext build`：通过。
- 前端测试：26 / 26 通过。
- ESLint：0 error；保留 8 个图片优化提示。
- 辨识专项 pytest：12 / 12 通过。
- 全量 pytest：951 / 951 通过。
- 浏览器实际流程：桌面与手机均可从正问进入辨识；AI 连接失败时显示明确错误，保留已答内容并提供主动选择的基础引导；提前结束可进入定问，再进入牡丹成卦。

final result: passed

---

# Design QA — 第 4 页「辨识」单问聚焦重构 v2

## 本轮问题与边界

- 用户明确指出旧版辨识页与第 3 页「正问」的视觉层级不一致：标题过小、单独的“贰”过于突兀，任务说明字体层级也不对应。
- 旧版把所有问题和回答持续堆叠成聊天记录，问题越多，页面越长，容易让用户在第七、八问时产生“还没问完”的疲惫感。
- 问题前使用的纸张底色八卦位图在页面上能看见正方形外缘，破坏成品感。
- 本轮只重构第 4 页「辨识」的版式与互动节奏；第 1–3 页和第 5 页的已定稿内容不重做。

## 已落实

1. 第 4 页改为与第 3 页同构的独立双栏首屏：左侧使用小号“观象之法 · 贰”、同尺度大标题“辨识”和同字体、同量级的三行任务提示；移除原先独立放大的“贰”。
2. 右侧不再渲染完整对话历史。页面始终只有当前问题、当前回答控件和必要的承接语；代码中不再存在 `dialogue-history`、`dialogue-row` 或逐项映射全部回答的聊天结构。
3. 回答后只保留上一问的一次短暂残影：向上移动并在 1.35 秒内淡出；残影绝对定位、`aria-hidden` 且不占据正文高度。新问题从下方轻微进入，形成“上一问退去、眼前一问出现”的节奏。
4. AI 分支继续显示对上一句的具体理解；基础整理分支明确标识为基础整理，不把固定程序冒充 AI。
5. 问答数量给出边界：AI 明示“通常 4–7 问 · 最多 8 问”，基础整理明示“共 7 问”。两条路径都支持“跳过这一问”和“已经说清，提前结束”。达到八问仍未完成时自动停止继续追问，并明确本次不生成 AI 改写建议。
6. 问题图标改用已有透明底 `fuxi-bagua-taiji.svg`，不再使用带宣纸方形底的 `bagua-seal.png`；桌面与手机均未出现可见正方形外缘。
7. 选项从圆角聊天卡改为宣纸上的墨色文字与细线；回答区、跳过与提前结束保持原生按钮／文本框语义和至少 44px 的触控目标。
8. `prefers-reduced-motion` 下关闭问题进入与残影动画，并直接隐藏残影；不用动画也能理解和完成流程。

## 实际浏览器检查

- 桌面：1440 × 900。辨识屏自身高度 900px；通过页面导航对齐后顶部位于固定页头下方约 67px，回答与提前结束控件底部约 734px；文档横向溢出为 0。
- 手机：390 × 844。辨识屏自身高度 844px；标题、当前问题、四个阶段选项、跳过与提前结束均落在单屏内，控件底部约 666px；文档横向溢出为 0。
- 连续问答：回答第一问后，页面只显示第二问“这件事现在走到了哪一步？”；旧聊天节点数量为 0；1.5 秒后上一问残影计算透明度为 0。
- 图标：当前问题使用透明底八卦 SVG，桌面与手机截图中没有纸张正方形外框。
- 提前结束：基础整理第二问时点击“已经说清，提前结束”，第 5 页「定问」正常出现；不会为了完成固定问数阻挡用户。
- 控制台：最终全新页面流程 0 warning / 0 error。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：24 / 24 通过。
- ESLint：0 error；5 个既有 warning，没有新增错误。
- 全量 `pytest`：945 / 945 通过。
- 未修改确定性排盘算法、规则版本、旧版入口，也未把现实背景作为卦象证据。

final result: passed

---

# Design QA — 第 5 页「定问」独立确认屏 v1

## 冻结依据与范围

- 已回读历史任务“总十页逻辑框架”中 turn `019f997d-9a53-7db2-88dd-2d15f2068827`：AI 可以根据辨识建议更准确的问法，但最终是否采用必须由用户自己判断。
- 第 5 页只承担“接受、修改或保留最终题目”。事实／未知整理仍属于第 4 页「辨识」；呼吸、复述与取三数仍属于第 6 页「成卦」。
- 第 1—3 页未修改；第 4 页的一问一答结构未重做，只把原本误放在第 4 页完成态中的“采用建议／保留原题”决策移交到独立第 5 页。

## 已落实

1. 新增独立 `100svh`「定问」屏：左侧以草书题名与大幅留白建立单一任务，右侧依次呈现原题、AI 建议或明确的“本次没有 AI 改写”状态、最终题目编辑区与唯一确认动作。
2. AI 建议与原题平行呈现；默认仍选择用户原题，不会因为 AI 返回建议而暗中改写。用户可以点击“采用这句”“保留原题”，也可以直接在最终题目中亲自修改。
3. 用户编辑后，原题／建议的选中状态立即撤销；只有点击或按 Enter 确认“就用这一问”后，题目才写回正式状态，并解除第 6 页门控。再次选择原题或建议会撤销先前确认，避免旧确认静默沿用。
4. 没有 AI 建议时，不伪造建议：页面明确说明本次使用基础整理或 AI 未提出改写，仍允许保留原题或自行修改。AI 接口失败时，第 4 页继续明确显示失败原因，并由用户主动选择基础引导。
5. 第 4 页完成态只说明“辨识已经足够／继续定问”，不再替用户选择最终题目；第 6 页的数字输入与观卦区域在定问确认前保持 `hidden`。
6. 视觉沿用宣纸、宋画长卷、墨色、朱砂、刘建毛草与楷体，不使用分类问卷、现代仪表盘或高密度卡片；原题与建议以两张横向纸笺关系组织，手机改为纵向阅读。
7. 所有操作使用原生按钮和文本框；手机上的题目选择与确认目标高度均不低于 44px。确认按钮显式支持 Enter／Space；焦点、`aria-pressed`、`aria-live` 状态和禁用条件完整。
8. `prefers-reduced-motion` 下取消本页选择层、确认按钮等过渡；页面不依赖动画才能理解或完成。

## 实际浏览器检查

- 桌面：1440 × 900。第 5 页自身高度为 900px；按页面内部坐标计算，标题、比较区与编辑区最下缘约为 740px，完整落在单屏安全范围内；文档横向溢出为 0。
- 手机：390 × 844。第 5 页自身高度为 844px；标题、比较区与编辑确认区最下缘约为 778px，完整落在单屏内；文档横向溢出为 0。
- 实际流程：正问 → AI 连接失败的明确提示 → 用户主动启用基础整理 → 完成辨识 → 进入定问 → 编辑题目 → 确认 → 第 6 页解除门控；再次选择“保留原题”后，确认被撤销且第 6 页重新隐藏。
- 键盘：最终确认按钮通过 Enter 实测，`aria-pressed=false → true`，状态播报为“最终题目已由你确认。”；鼠标／触屏点击使用相同原生按钮路径。
- 控制台：0 warning / 0 error。
- 本地 AI 上游未连接，因此实际浏览器验收覆盖了明确失败与主动基础整理状态；AI 建议分支通过构建、类型检查与条件渲染代码审计，未用固定程序冒充 AI 返回。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：23 / 23 通过。
- ESLint：0 error；9 个既有 warning，本轮未新增 lint error。
- 全量 `pytest`：945 / 945 通过。
- 未修改确定性排盘算法、规则版本、旧版入口或现实信息证据边界；未部署、未提交、未推送。

final result: passed

---

# Design QA — 第 2 页「明法」悬停强调与文案精简 v5

## 比较目标

- Source visual truth：`qa/method-desktop-v4-default.png`，结合本轮用户明确提出的三项覆盖要求：移除“约三分钟”、移除 CTA 旁“问”字方印、增加鼠标悬停放大加粗并在移开后复原。
- 桌面默认态：`qa/method-desktop-v5-default.png`，1440 × 900 CSS px。
- 桌面悬停态：`qa/method-desktop-v5-hover.png`，第二句强调状态。
- 桌面点击书写态：`qa/method-desktop-v5-writing.png`。
- 手机默认态：`qa/method-mobile-v5-default.png`，390 × 844 CSS px。
- 全屏前后对比：`qa/method-v4-vs-v5.png`。
- 源图与实现均为 1× 密度、相同 CSS 视口；无需密度归一化。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与排印：三句继续使用刘建毛草本地字体。鼠标进入或键盘可见焦点时，当前句由 72px 视觉基准放大到 `scale(1.34)`，合成字重升至 700，并增加 0.28px 墨色描边和对比度；其余两句退为淡墨。悬停截图中第二句宽度由约 324px 增至约 434px，变化明确可见。
- 状态恢复：`onPointerLeave` 与 `onBlur` 均将预览状态恢复为 `null`，离开后回到默认字号、400 字重和淡墨。点击仍保留既有两倍逐字书写动画，不与悬停状态冲突。
- 文案与控件：页面不再渲染“约三分钟”；“开始正问”只保留文字与朱砂细线，旁边的“问”字小方印已完全移除。按钮宽度同步由 132px 收至 116px，视觉中心不偏移。
- 布局：右侧文案上移后仍保持两段清晰节奏；桌面悬停态与右侧说明保留约 221px 间距。390px 手机无横向溢出，CTA 完整位于首屏底部。
- 颜色与图像：沿用既有宣纸、淡墨、朱砂和宋画长卷资产，未引入新视觉资产；首页资源和开场节奏未修改。
- Copy：本页仅剩“接下来 / 我们尝试观象”“请闭上眼睛 / 做三个呼吸”“开始正问”，没有提前出现第 3 页内容。
- 交互与无障碍：三句均为原生按钮，悬停、键盘焦点、触屏点击语义保留；`prefers-reduced-motion` 继续取消过渡和逐字动画。

## Comparison history

### 第一轮

- [P2] 旧悬停倍率仅 `scale(1.08)`，实际视觉变化过弱，用户无法明确感知放大。
- [P2] “约三分钟”与 CTA 小方印在当前极简内容中形成多余信息和装饰。

### 修复后

- 悬停倍率提高至 `scale(1.34)`，同时增加 700 字重、轻描边与墨色对比；悬停态截图确认没有挤压右侧说明。
- 删除两个多余节点及其响应式样式，收紧 CTA 内边距；桌面与手机复核均无裁切或横向溢出。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：22 / 22 通过。
- ESLint：0 error；9 个既有 warning，本轮未新增 lint error。
- 浏览器控制台：应用页面 0 warning / 0 error。
- 未部署、未提交、未推送。

final result: passed

---

# Design QA — 第 3 阶段「正问」独立一屏 v1

## 冻结依据

- 已回读历史任务“总十页逻辑框架”中 turn `019f9975-5230-7623-9247-c47338e17118` 的语音原文。
- 本屏只承担“写下一件具体而真实的事”：一个问题输入框、四个精选例句。分类、事实与未知、AI 对话、定问和成卦不在本屏提前出现。
- 第 1 页「入境」与已定稿的第 2 页「明法」未作修改。

## 已落实

1. 第三页成为独立的 `100svh` 屏幕，以“观象之法 · 壹／正问／写下一件真实具体的事”建立单一视觉任务。
2. 页面只有一个主输入框；用户可先按自然方式写，下一阶段再辨识事实、未知与真实需要。
3. 四个精选例句分别覆盖工作、合作、关系与个人规划；点击任一句只会填入输入框，仍可继续修改。
4. 后续“辨识—成卦—观卦”整体由 `hidden` 门控，不会随滚动提前露出。问题至少六个字且用户主动点击“写好了，继续辨识”后，才显示下一阶段。
5. 桌面 1280 × 720 实测：第三页高度 720px，标题区与输入区完整落在一屏内；四个例句数量正确，页面没有横向溢出。
6. 交互实测：例句可填入问题，继续按钮由禁用转为可用；确认后第四阶段显示并平滑进入。复位后已把预览恢复到空白的第三页审定状态。
7. 键盘焦点、触屏目标和 `prefers-reduced-motion` 均有对应样式；浏览器控制台 0 warning / 0 error。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：22 / 22 通过。
- 未修改确定性排盘引擎、规则版本、旧版入口或前两页已收口资源。

final result: passed

---

# Design QA — 第 2 页「明法」两倍书写与正问入口 v4

## 比较目标

- 选定视觉方向：`C:\Users\27622\.codex\generated_images\019f9e9b-9c3e-7820-ba92-7978b3aa47d0\exec-d1e1c2af-0d8e-425e-b6df-c4718fb578b5.png`。
- 桌面默认态：`qa/method-desktop-v4-default.png`，1440 × 900 CSS px。
- 桌面书写中段：`qa/method-desktop-v4-writing-mid.png`；完成态：`qa/method-desktop-v4-writing-final.png`。
- 手机默认态：`qa/method-mobile-v4-default.png`；完成态：`qa/method-mobile-v4-writing-final.png`，390 × 844 CSS px。
- 视觉方向与实现并排比较：`qa/method-source-vs-v4.png`。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 左侧三句保持刘建毛草字体、三行无标点和原有错落。点击任一句后，该句相对默认字号严格放大至 `scale(2)`；原文字先退去，再按单字时序以墨迹模糊、显形、收锋的节奏完整写出，重复点击可重新播放。
- 非当前句退为淡墨，当前句完成后保持深墨。桌面端放大句与右侧说明保留约 38px 安全间距；手机 390px 宽度下完成态右边缘约 365px，没有横向裁切。
- 右侧只保留“约三分钟”“接下来 / 我们尝试观象”“请闭上眼睛 / 做三个呼吸”，没有加入第 3 页输入、AI 辨识或排盘内容。
- “开始正问”改为屏幕下方中央的小型山水式文字入口，使用朱砂细线和 18px 小印记，不再是大块印章按钮；桌面与手机首个视口均可见。
- “开始正问”仍是真实状态确认：实测 `aria-pressed=false → true`，第 3 页由 `hidden=true → false`，焦点最终落到 `#inquiry-title`。
- 鼠标、键盘焦点、触屏点击均使用原生按钮语义；`prefers-reduced-motion` 下取消逐字动画与过渡，直接显示完整两倍文字。
- 首页构图、雾中入境、飞鸟、开场节奏和首页资源未修改；确定性排盘、规则版本与 AI 边界未修改。
- 浏览器控制台：0 warning / 0 error。

## Comparison history

### 第一轮

- [P1] 两倍放大后的第二句右边缘与右侧文案相碰。
- [P2] 选中句残留默认文字形成轻微重影；键盘焦点框在两倍状态下过于突兀。
- [P2] “开始正问”最初贴近视口下缘，视觉上接近被裁切。

### 修复后

- 放大态向左平移 42px，实测句子右边缘 870.8px、右侧说明起点 908.4px。
- 书写态隐藏默认字层，取消两倍态额外外框；逐字墨迹动画保持清晰。
- CTA 上移到与首页入口相近的底部中央位置；桌面按钮底边约 838px，手机约 809px。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：22 / 22 通过。
- ESLint：0 error；9 个既有 warning，本轮未新增 lint error。
- 未部署、未提交、未推送。

final result: passed

---

# Design QA — 第 2 页「明法」留白与正问入口 v3

## 比较目标

- Source visual truth：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-662d3d2b-4d6b-47d1-b0a7-9907f33cf146.png`，即用户指出左侧排版过紧、右侧文字层级与按钮仍不符合十页逻辑的截图。
- Revised desktop：`qa/method-desktop-v3.png`，1440 × 900 CSS px，默认状态。
- Revised desktop active state：`qa/method-desktop-active-v3.png`，1440 × 900 CSS px，第二句点亮状态。
- Revised mobile：`qa/method-mobile-v3.png`，390 × 844 CSS px。
- Full-view combined comparison：`qa/method-source-vs-v3.png`。本轮依据用户明确给出的内容结构做层级和节奏比较，不以旧版逐像素复刻为目标。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 左侧排印：保持用户已确认的刘建毛草字体和三行无标点文字；桌面行距由 `.12em` 拉开至 `.38em`，第二、三行分别增加水平错落，三句不再挤成一块。手机使用 `.2em` 行距和收敛后的错位，在 390 px 宽度下没有横向溢出。
- 页面命名：完全移除“第二阶段 · 明法”的可见提示；本屏作为十页流程中的独立第 2 页存在，不在页面内展示阶段编号。
- 内容收束：右侧只呈现“约三分钟”“接下来 / 我们尝试观象”“请闭上眼睛 / 做三个呼吸”和“开始正问”，删除旧版所有解释性段落与过程预告，也没有提前出现第 3 页输入内容。
- 正问入口：原椭圆按钮改为 2 × 2 排列的四字朱砂印章；默认显示“开始 / 正问”，确认后变为“已定 / 正问”。按钮仍是真实状态确认，不是锚点。
- 交互：三句继续支持鼠标指向、键盘聚焦和触屏点击；当前句为深墨，另外两句退为淡墨。点击朱印后实测 `aria-pressed=true`、第 3 页解除 `hidden`，焦点落到 `#inquiry-title`。
- 响应式与动效：1440 × 900 和 390 × 844 均无裁切、遮挡或横向溢出；移动端朱印为 94 px 方形触控目标。`prefers-reduced-motion` 继续取消逐句动画、行文字过渡和按钮过渡，文字保持可见。
- 视觉资产：首页与长卷背景资源均未修改；没有改动首页构图、飞鸟、雾中入境或开场节奏。
- 浏览器控制台：0 warning / 0 error（仅 Vite 连接 debug 与 React DevTools info）。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：21 / 21 通过。
- ESLint：0 error；9 个既有 warning，本轮未新增 lint error。
- 未修改确定性排盘引擎、规则版本、AI 辨识逻辑、旧版入口或第 1 页首页。

final result: passed

---

# Design QA — 首页「雾中入境」流畅度优化 v11

## 比较目标

- Source visual truth：`qa/entry-v11-before-1380-03-mist.png`
- Revised implementation：`qa/entry-v11-after-1380-03-mist.png`
- Full-view comparison：`qa/entry-v11-before-after-03-comparison.png`
- Transition sequence：`qa/entry-v11-transition-contact-sheet.png`
- Viewport：1380 × 900 CSS px；源图与实现截图均为 1380 × 900 px，1× 密度，无缩放归一化差异。
- State：开场约 3.0 秒的雾景峰值；另检查 5.2、6.0、6.4、7.0、8.9 秒连续状态。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与文字：标题、题句和落款均属于原始水墨位图，优化前后字形、字重、位置和内容未改变。
- 间距与构图：标题、主山、树枝、湖面和飞鸟的空间关系保持一致；1380 × 900 与 390 × 844 均未出现裁切或漂移。
- 色彩：宣纸底色、浅墨雾层与朱砂点缀保持原有色阶；WebP 转换未产生可见偏色。
- 图片质量：六张首屏 PNG 共 11.81 MB，转换为质量 90 的响应式 WebP 后共 0.83 MB，减少约 93%；同屏比较未发现可见压缩块、边缘光晕或文字损伤。
- 文案：可见文案与无障碍文本均未改变。
- 聚焦区域比较不需要：本次修改只影响全屏位图解码与整体透明度，关键文字本身嵌在同一源图中；全屏同尺寸比较足以确认视觉保真。

## Comparison history

### 第一轮

- [P1] 用户可感知的雾化卡顿。
- 证据：首屏在首个动画帧就开始运动，同时解码约 11.81 MB PNG；两个全屏图层持续执行透明度与缩放合成，雾景退出还集中在约 0.5 秒内。
- 修复：
  1. 将六张响应式首屏素材改为 WebP，总体积降至 0.83 MB。
  2. 动画开始前等待最终首页与雾景图片完成 `decode()`，并保留 1.8 秒容错上限。
  3. 移除两个全屏图层的缩放，仅保留 GPU 友好的 `opacity`。
  4. 改为线性透明度曲线，将雾景退出和最终首页显现分别拉长；两张标题不同时处于可见状态，避免重影。

### 修复后

- 桌面连续帧：`qa/entry-v11-after-1380-05-birds.png`、`qa/entry-v11-after-1380-06-dissolve.png`、`qa/entry-v11-after-1380-064-emerge.png`、`qa/entry-v11-after-1380-07-emerge.png`、`qa/entry-v11-after-1380-09-final.png`。
- 手机连续帧：`qa/entry-v11-after-390-03-mist.png`、`qa/entry-v11-after-390-06-dissolve.png`、`qa/entry-v11-after-390-09-final.png`。
- 雾景按单调透明度淡回宣纸，最终山水再连续显现；连续帧无标题重影、突跳或错位。
- 浏览器控制台 warning / error：0。

## 工程验证

- `vinext build`：通过。
- `node --test tests/rendered-html.test.mjs`：15 / 15 通过。
- 未修改确定性排盘引擎、规则版本、旧版入口或 Phase 1 业务边界。

final result: passed

---

# Design QA — 第 2 阶段「明法」原话校正版 v2

## 比较目标

- Source visual truth：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-d27d3f49-23b5-49b2-b605-f01d32d9b80d.png`，即用户指出左侧文字消失、右侧过密的缺陷截图。
- Revised desktop：`qa/method-desktop-final.png`，1440 × 900 CSS px，1× 密度，默认常驻状态。
- Revised desktop active state：`qa/method-desktop-active-final.png`，1440 × 900 CSS px，1× 密度，第二句点亮状态。
- Revised mobile active state：`qa/method-mobile-active-final.png`，390 × 844 CSS px，1× 密度。
- Full-view combined comparison：`qa/method-source-vs-final.png`。源截图去除 108 px 浏览器顶栏后等比缩放至 1440 px 宽并置于 1440 × 900 画布；实现图保持 1440 × 900。源图用于缺陷和整体层级比较，不作逐像素重现目标，因为本轮用户原话明确覆盖了旧版内容结构。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与排印：三句改用本地 `Liu Jian Mao Cao Local` 开源草书字体；严格呈现为“在天成象 / 在地成形 / 变化见矣”三行，没有视觉标点。桌面字号约 88 px，手机约 50 px；字形飘逸但仍可辨认。
- 间距与构图：桌面为左侧经典、右侧准备引导的双栏长卷；右侧删除四步流程和两段产品说明后，留白和视觉重心明显恢复。390 × 844 下转为纵向长卷，三句、引导和确认按钮完整落在第二屏内，无横向溢出。
- 色彩与视觉变量：沿用宣纸、墨色、朱砂和原长卷背景；当前句为深墨，其他两句退至 0.32 透明度，默认三句保持 0.62 透明度，未引入新的卡片或现代界面色。
- 图片质量：继续使用现有长卷与首页已冻结资源；本轮没有生成或替换首页图像，也没有发现遮罩边缘、位图拉伸或压缩伪影。
- 文案：右侧只保留“约三分钟”“一步一步看清心中的疑惑”“慢慢做三个呼吸”和进入正问的确认，不再提前解释四个后续阶段，也没有第三页输入内容。
- 状态与交互：逐句按钮支持鼠标悬停、键盘聚焦和触屏点击。实际浏览器检查中，点亮第二句后状态为 `0.32 / 1 / 0.32`，`aria-pressed` 仅当前句为 `true`。确认按钮由 `aria-pressed=false` 变为 `true`，显示状态播报，解除第三页 `hidden` 并把焦点移至 `#inquiry-title`。
- 无障碍：三句使用原生按钮，标题有简洁的整体 `aria-label`；焦点有朱砂下划线；按钮触控高度满足移动端操作。`prefers-reduced-motion` 下取消逐句动画和过渡，并直接保持三句可见。
- 浏览器控制台：0 warning / 0 error。

## Comparison history

### 第一轮发现

- [P1] 左侧三句只在入场时闪现，之后可能回到 `opacity: 0`；旧版逐句凸显状态被删除。
- [P1] 右侧定义、说明段落、四步流程和确认文案同时出现，偏离用户原话中的“准备引导”，信息密度过高。
- [P2] 三句保留了逗号和句号，字体气质偏规整，未达到“三行、无标点、飘逸毛笔字”的要求。

### 修复与复核

- 基础状态改为淡墨常驻，入场动画仅负责从墨中浮现；动画类缺失时也不会重新隐藏。
- 恢复逐句交互，并补齐 React 选中状态、原生按钮语义、触屏点击和键盘焦点。
- 引入 Google Fonts 官方仓库的刘建毛草字体与 OFL 许可证，只用于三句经典文字；字体已按 10 个所需汉字裁成 3.3 KB WOFF2，未给首页增加 4.9 MB 原始字体负担。
- 删除四步流程和长篇说明，重排为三分钟、引导、三个呼吸、状态确认。
- 桌面、手机、点亮态和确认态复核后，无新的 P0 / P1 / P2。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：21 / 21 通过。
- ESLint：0 error；9 个既有 warning，均为原有 `<img>` 优化提示或既有 SVG `aria-hidden` 提示，本轮未新增 lint error。
- 未修改首页结构、首页资源、确定性排盘引擎、规则版本或旧版入口。

final result: passed

---

# Design QA — 第 2 阶段「明法」独立一屏 v1

## 冻结依据与现状

- 冻结依据：`experience-rebuild-v1.md`、`PROJECT_HANDOFF_2026-07-26.md` 与本轮用户指令。
- 历史对话“总十页逻辑框架”在本轮读取时暂不可用；按用户指令以冻结文档继续，未自行扩展第 2 阶段范围。
- 改造前证据：`qa/method-v1-before-1380.png`。
- 改造后桌面：`qa/method-v2-after-1380.png`。
- 准备确认态：`qa/method-v2-ready-1380.png`。
- 改造后手机：`qa/method-v2-after-390.png`。
- 视口：桌面 1380 × 900；手机 390 × 844。

## 已落实

1. 第 2 屏明确命名为“第二阶段 · 明法”，保持宋画长卷、宣纸、墨色、朱砂、书法和留白体系，未改动第 1 屏首页的构图、素材或开场节奏。
2. “在天成象／在地成形／变化见矣”三句按 0.55s、1.25s、1.95s 的层次从模糊墨色中依次显影；引文出处最后出现，形成可感知的阅读顺序。
3. 解释内容收束为“观象是什么”“约三分钟”“正问—辨识—成卦—观卦”与方法边界；本屏不出现输入框、AI 辨识或成卦控件。
4. “我已准备好”从锚点改为真实按钮状态：`aria-pressed=false → true`，朱砂印从“明”变为“定”，文案变为“已定心 · 正问”，并通过 `aria-live` 播报确认结果。
5. 第 3 屏在确认前使用 `hidden` 脱离布局和无障碍树；确认后才显示、平滑进入，并把焦点交给“正问”标题。顶部“开始问”在未确认时也会把用户带回准备按钮，不能绕过状态。
6. 桌面 1380 × 900 与手机 390 × 844 均能在单个视口内完整呈现本阶段内容；手机确认按钮高 56px、宽约 335px，满足触屏目标尺寸。
7. 按钮使用原生 `button`，并显式处理 Enter / Space；焦点样式可见。`prefers-reduced-motion` 下取消逐句动画、过渡和延迟，直接显示完整内容，并即时进入下一屏。

## 视觉与交互结论

- P0：无。
- P1：无。
- P2：无。
- 桌面构图由改造前的“长说明 + 下方被裁切操作”变为左侧经典、右侧方法与确认的完整一屏；主次清楚，确认动作在首个视口内可见。
- 手机采用纵向长卷阅读顺序，经典、释义、四步与确认按钮没有互相遮挡、横向溢出或提前露出第 3 屏。
- 确认态有文字、色彩、印章和无障碍播报四重反馈，不依赖单一颜色表达。

## 证据边界

- 浏览器截图验证桌面与手机视觉；DOM 与状态检查验证第 3 屏门控、确认状态、焦点目标和触控尺寸。
- 本地浏览器的自动按键注入未能可靠移动系统焦点，因此键盘结论同时依据原生按钮语义、显式 Enter / Space 处理与可见焦点样式；仍建议用户在真实设备验收时再走一遍物理键盘 Tab / Enter。
- 减少动态效果依据命中的专用 CSS 降级规则检查；本轮浏览器环境未提供切换系统 `prefers-reduced-motion` 的能力。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：21 / 21 通过。
- 未修改确定性排盘引擎、规则版本、旧版入口或首页已收口资源。

final result: passed

---

# 成卦页视觉 QA

## 对照对象

- source visual truth: `C:\Users\27622\.codex\generated_images\019fb34f-2804-7d23-8369-4a4c228b1aac\exec-05cf9805-604d-4066-96e5-1c1e016335d1.png`
- implementation screenshot: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-desktop-final5.png`
- mobile arrival screenshot: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-mobile-arrival.png`
- combined comparison evidence: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-comparison-final.png`

## 归一化信息

- source pixels: 1723 × 913，包含浏览器外壳。
- desktop implementation CSS viewport: 1280 × 720，devicePixelRatio 1.25；浏览器截图传输为 987 × 712，仅包含应用画面。
- mobile implementation CSS viewport: 390 × 844；截图为点击“开始卜卦”后自动到达成卦页的空值状态。
- combined comparison: 两张图保持原始宽高比并统一到 800px 高，中间留 24px 分隔；未拉伸或裁剪设计主体。
- state: 第六页首次进入，三个输入为空；落瓣动画运行中。

## 全画面对照

- 宋画长卷、宣纸、墨色、朱砂、书法与大面积留白保持现有设计系统。
- 选定方案的“散瓣 + 一笔风势”已经作为真实位图资产进入取数区，没有使用 CSS 绘图或 SVG 近似。
- 根据用户本轮明确修订，生成参考中的 `1—999` 已从三个输入中移除；范围说明改到左侧说明文字下方。
- 三处取数继续保持同一基线，遵循用户此前明确要求，不采用生成参考中的错落高度。
- 三朵牡丹分别以背景花托的锚点定位：44.3% / 66.8%、59.5% / 33.8%、78.5% / 51%，花头与花托在桌面和手机画面均连续。

## 聚焦区域对照

- 取数区：桌面 DOM 实测三组边界为 x=466.6–685.7、711.3–930.4、956.0–1175.2，bottom=652.6，均在 1280 × 720 CSS 视口内。
- 手机取数区：三组边界为 x=20–129.7、132.7–242.5、245.5–355.2，点击跳转后的 bottom=618.7，均在 390 × 844 首屏内。
- 范围提示：桌面为 11px 楷体、单行、244px 宽；手机为 9px、单行，没有继承上方 25.6px 书法正文。
- 输入交互：三个 number input 的 placeholder 均为 null，min=1、max=999，aria-describedby 均指向范围说明；实测可输入 17、24、37。

## 必查表面

- Fonts and typography: 标题继续使用刘建毛草，正文继续使用既有书法/楷体栈；新增说明使用较轻楷体，不与主文案争夺层级。
- Spacing and layout rhythm: 桌面与手机三处取数对齐；桌面底部留出至少约 67px 的 CSS 视口余量，手机完整进入首屏。
- Colors and visual tokens: 沿用 `--ink`、`--ink-soft`、`--mist`、`--cinnabar-dark`；新资产为低饱和暖灰飞白，不引入新色系。
- Image quality and asset fidelity: 风痕为 OpenAI 图像生成后色键去底的透明 PNG；牡丹和花瓣继续使用现有高分辨率透明资产，无方块、白边或额外底图边缘。
- Copy and content: 左侧范围说明为“取1-999之间的数字，填入右侧文字下方”；三处仍为“一息 / 上卦取数”“二息 / 下卦取数”“三息 / 动爻取数”。

## 对照迭代历史

1. iteration 1
   - finding [P1]: 范围提示被 `.final-question-heading > p:last-child` 覆盖，实际为 25.6px 并折成两行。
   - finding [P1]: 桌面三组取数 bottom=745，低于 720px 首屏。
   - fixes: 提高选择器优先级，提示改为 11px 单行；统一取数组的纵向偏移。
2. iteration 2
   - post-fix evidence: 提示实测 11px、244px、单行；取数组 bottom 降至 695.8。
   - finding [P2]: 飞白风痕处于负层级，视觉存在感不足。
   - fix: 取数 field 建立独立堆叠上下文，风痕改为 z-index 0，取数组改为 z-index 1；取数组进一步上移。
3. final
   - post-fix evidence: 桌面三组 bottom=652.6；手机跳转后三组 bottom=618.7；桌面与手机均完整进入首屏。
   - 浏览器控制台 errors/warnings: 0。
   - 未发现仍需处理的 P0/P1/P2。

## 交互与响应式验证

- 实际浏览器完整走通：了解观象之法 → 开始正问 → 填写问题 → 继续辨识 → 提前结束 → 继续定问 → 开始卜卦。
- 桌面和手机均验证了跳转落点。
- 三个数字输入均实际填写并读回；空状态不显示 `1—999`。
- `prefers-reduced-motion` 仍沿用现有成卦页降级规则，没有改变确定性排盘或任何算法。

## Follow-up Polish

- 无阻断项。风痕的浓淡与静态散瓣密度属于后续用户主观审美微调范围。

final result: passed

---

# 第六页成卦：取数移至左侧、花区净空 QA（2026-07-31）

## 对照材料

- source visual truth: `C:\Users\27622\AppData\Local\Temp\codex-clipboard-7f0ab26e-7ac8-4375-840d-867a34255f74.png`
- desktop implementation: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-left-inputs-medium.png`
- wide-screen DOM verification: 1920 × 1080 CSS viewport，三朵牡丹和取数区均在视口边界内。
- mobile implementation: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-left-inputs-mobile.png`
- full-view comparison: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-left-inputs-comparison.png`
- focused comparison: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-left-inputs-focus-comparison.png`

## 归一化与状态

- source pixels: 1896 × 1018，包含 Chrome 外壳；对照时从 y=108px 裁去浏览器外壳，保留页面主体。
- desktop visual capture: 988 × 891 CSS viewport / 972 × 882 browser-rendered pixels，devicePixelRatio 1；状态为成卦页，输入值 3 / 6 / 9，落瓣动画运行中。
- wide desktop verification: 1920 × 1080 CSS viewport，成卦段顶部 y=67.7px，取数区 bottom=616.4px；三朵牡丹最右边界分别为 1037.7px、1320.1px、1689.5px，均完整入画。
- mobile visual capture: 390 × 844 CSS viewport / 375 × 811 browser-rendered pixels；从首页完整走到“开始卜卦”后的到达状态，再填写 3 / 6 / 9。
- full comparison 将裁去浏览器外壳后的 source 与 desktop implementation 等高并排；focused comparison 单独放大标题、三行说明和三组取数。

## Findings

- 第一轮 source 中三组“一息 / 二息 / 三息”侵入牡丹枝叶，花区与表单争夺视觉焦点，属于 P1。
- 第一轮右侧 S 形飞白风痕在取数移走后失去功能依据，继续保留会形成额外装饰层，属于 P2。
- 修复后取数 fieldset 已整体移入 `.casting-heading`，位于范围说明下方；`.casting-number-workspace` 只保留装饰花瓣，风痕图片与对应 CSS 完全移除。
- 修复后未发现仍需处理的 P0 / P1 / P2；花丛成为独立画面，左侧仍保持清楚的题字—说明—范围—取数阅读顺序。

## 必查表面

- Fonts and typography: “成卦”、三行书法说明、“一息 / 二息 / 三息”和楷体小字继续沿用既有字体变量；取数行字号收紧但未改变字重和色彩。桌面与手机均无异常断行、截断或豆腐块式大段文字。
- Spacing and layout rhythm: 桌面取数采用三等分横排，三组基线齐平；花区从左侧表单中解放。1920 宽屏中左栏 x=321.4–731.3px，右侧花区 x=833.3–1665.4px，二者无重叠。手机到达时取数区 y=223.2–266.2px，三朵花 y=378.2–526.5px，均在 844px 首屏内。
- Colors and visual tokens: 继续使用既有宣纸、墨色、朱砂和雾灰 token；未引入新色块、边框、卡片或阴影。
- Image quality and asset fidelity: 三朵牡丹、枝叶和花瓣仍使用原有 PNG / WebP 资产，单花锚点与动画参数未改；只对整幅场景在桌面做统一轻微右移，手机恢复居中。风痕位图已删除，不存在透明方块或遗留边缘。
- Copy and content: 左侧范围说明保持用户指定文字“取1-999之间的数字，填入右侧文字下方”；三组说明保持“一息 / 上卦取数”“二息 / 下卦取数”“三息 / 动爻取数”。

## 交互、响应式与无障碍

- 实际浏览器完整走通：首页 → 了解观象之法 → 开始正问 → 填写问题 → 继续辨识 → 提前结束 → 继续定问 → 开始卜卦 → 成卦。
- 三个 number input 在桌面和手机均可触达、填写和读回；保留 min=1、max=999、inputMode=numeric、可访问标签和范围说明关联。
- 手机 390 × 844 的自动到达位置完整呈现标题、说明、范围提示和三组取数，花丛从其下方展开，没有横向溢出或文字压花。
- 1920 × 1080、988 × 891、390 × 844 三个断点均验证三朵牡丹完整入画；花瓣数量仍为 54（每朵 18），风痕元素数量为 0。
- `prefers-reduced-motion` 继续沿用既有成卦页降级规则；本轮未改动画轨迹、大小、颜色、透明度或快慢参数。
- 浏览器控制台 errors / warnings: 0。

## 工程验证

- Vinext production build: passed。
- Node rendered/interaction tests: 26 / 26 passed。
- ESLint: 0 errors，11 个既有 warning（`<img>` 优化提示与既有 ARIA 提示）；未新增 lint error。
- `git diff --check`: passed。
- 未修改确定性排盘、规则版本、Python 引擎或第 7 页以后内容；本轮未发布。

## 对照迭代历史

1. iteration 1: source 显示取数文字覆盖花丛，S 形风痕承担取数区装饰。
2. iteration 2: 取数整体移到左栏，花区净空；删除风痕资产与样式；桌面花景作为一个整体轻微右移。
3. final: desktop focused comparison 显示左侧层级清楚、三组取数齐平；mobile arrival 显示全部取数首屏入画；1920 宽屏 DOM 证实三朵牡丹完整入画且与表单无重叠。

## Follow-up Polish

- 无阻断项；后续如继续微调，应保持花朵锚点、花托衔接、落瓣大小颜色与现有动画参数冻结。

final result: passed

---

# 第六页成卦：取数横排与花瓣速度分层 QA（2026-07-31）

## 对照材料

- source visual truth: `C:\Users\27622\AppData\Local\Temp\codex-clipboard-73238fb6-a887-47e8-99e7-319c79eae288.png`
- desktop implementation: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-desktop-input-right-final.png`
- mobile arrival implementation: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-mobile-input-right.png`
- full comparison: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-comparison-input-right.png`
- focused comparison: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-comparison-input-right-detail.png`

## 归一化信息

- source pixels: 1917 × 1017，含 Chrome 外壳；用户提供的桌面成卦页，取数值为 3 / 6 / 9。
- desktop CSS viewport: 1280 × 720，devicePixelRatio 1.25；浏览器截图传输为 987 × 712，取数值为 3 / 6 / 9。
- mobile CSS viewport: 390 × 844；浏览器截图传输为 375 × 811；状态为点击“开始卜卦”后自动到达成卦页、三个输入为空。
- full comparison 将三张图等高归一到 720px，不拉伸画面；focused comparison 仅比较牡丹、文字与取数关系。
- 桌面截图传输右侧裁切来自浏览器传输宽度与 CSS 视口不一致；DOM 实测第三组右边界为 1175.2px，仍在 1280px CSS 视口内，因此不作为布局缺陷。

## Findings

- [P1] 一息文字与第一朵牡丹重叠。
  - Location: `.peony-number-1` 与第一朵牡丹下缘。
  - Evidence: source detail 中“一息”覆盖花瓣；修订后第一朵牡丹 bottom=531.2px，三组文字顶部 y=552.8px，留有 21.6px 间距。
  - Impact: 原布局破坏花朵完整性，也让取数层级不清。
  - Fix: 三组取数统一下移，并改为文字在左、输入在右的横排结构。

- [P2] 第一轮横排后文字与数字间距偏松。
  - Location: `.peony-number` 的第一列最小宽度与 column gap。
  - Evidence: 首轮桌面实测间距 28.9px；收紧后为 9.7px，手机为 2px。
  - Impact: 间距过大会让数字像独立元素，削弱“每一息对应一个数”的关系。
  - Fix: 桌面第一列改为 `minmax(60px, auto)`，间距改为 `clamp(4px, .55vw, 8px)`；手机保持紧凑双列。

## 必查表面

- Fonts and typography: 保留现有书法标题、朱砂“一息 / 二息 / 三息”和楷体说明；数字仍使用现有书法字体，仅改变位置，不改变大小、颜色或字重。
- Spacing and layout rhythm: 桌面三组底部均为 610.8px，完整位于 720px 首屏；手机三组底部均为 594.2px，完整位于 844px 首屏。三组基线齐平，文字与数字形成一一对应的横向节奏。
- Colors and visual tokens: 花瓣、牡丹、墨色、朱砂及飞白风痕未改；本轮没有引入新色值或新表面。
- Image quality and asset fidelity: 牡丹、花瓣与风痕继续使用既有真实 PNG / WebP 资产；未增加 CSS 图形、SVG 近似或占位图。
- Copy and content: 左侧提示严格保持“取1-999之间的数字，填入右侧文字下方”。

## 动画与交互验证

- 18 条花瓣轨迹的大小、颜色、旋转、翻滚与路径参数未改。
- 时长从原先较接近的 11.8–18.1 秒扩展为 8.5–23.2 秒，形成明显的快、中、慢层次。
- 所有轨迹继续使用 `linear` 计时、GPU `translate3d` 与连续关键帧；没有加入停顿、步进或突变。
- `prefers-reduced-motion` 仍关闭落花动画。
- 三个数字输入在桌面和手机均实际填写并读回 3 / 6 / 9；输入保持 min=1、max=999 与无占位符。
- 实际浏览器完整走通：首页 → 正问 → 辨识提前结束 → 定问 → 开始卜卦 → 成卦。
- 当前成卦页浏览器控制台 errors / warnings: 0。

## 对照迭代历史

1. iteration 1: 发现 source 中“一息”覆盖花瓣，横排初稿的文字数字间距为 28.9px。
2. iteration 2: 三组统一下移，输入改到文字右侧；桌面间距收紧到 9.7px，手机间距为 2px。
3. final: 桌面三组 bottom=610.8px；手机跳转后 bottom=594.2px；未发现仍需处理的 P0/P1/P2。

## Follow-up Polish

- 无阻断项。后续只需根据用户主观观感微调快慢比例，不需再改变花瓣大小、颜色或轨迹。

final result: passed

---

# 第六页成卦：大花瓣离花透明度与提示语复检（2026-07-31）

- implementation screenshot: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-petal-opacity-fix.png`
- 花瓣 PNG 本体为 217 × 220；透明像素仅在图外，花瓣主体为不透明纹理，问题来源确认是动画在尚未离开花朵时已经开始降低整图 opacity。
- 修复后 0% / 10% / 24% / 47% 均保持 opacity=1；花瓣越过花朵范围后才在 47%–100% 之间缓慢淡出。大小、色彩、路径、旋转、翻滚和快慢时长全部未改。
- 连续 20 次浏览器采样共捕获 94 个仍在花朵图像范围内的大花瓣状态，opacity 最小值与最大值均为 1；最终画面同时捕获两枚 108px 大花瓣，opacity 均为 1。
- 提示语已改为“取1-999之间的数字，填入下方文字右侧”，与三组文字右侧的实际输入位置一致。
- 真实浏览器复检：54 枚动态花瓣、0 个风痕元素；控制台 errors / warnings 为 0。
- Vinext production build passed；Node tests 26 / 26 passed；ESLint 0 errors（11 个既有 warning）。
- 未修改牡丹位置、花托衔接、花瓣资产、确定性排盘或后续页面；本轮未发布。

final result: passed

---

# 第六页成卦：动态花瓣独立顶层修复（2026-07-31）

- implementation screenshot: `C:\Users\27622\.codex\worktrees\4f6b\Abalo-s-project\sites\hosted-app\design-qa-casting-petal-layer-fix.png`
- 根因复核：此前每组动态花瓣嵌套在各自 `.peony-bloom` 内；牡丹容器因定位 transform 形成独立 stacking context。花瓣的局部 z-index 只能在本朵牡丹内部生效，无法越过后渲染的其他牡丹容器，因此跨花重叠时会被另一朵半透明牡丹图像压住，产生“只有重叠部分变透明”的现象。上一轮仅调整 opacity 的诊断不完整。
- 修复：三朵牡丹图像统一保留在 z-index 1；54 枚动态花瓣移出三个牡丹 stacking context，进入覆盖整幅画面的 `.peony-petal-layer`，该层为 z-index 2。牡丹内部动态花瓣数量由 54 降为 0，顶层动态花瓣数量为 54。
- 三个 `.peony-petal-origin` 与三朵牡丹的 x / y / width / height 实测逐项完全一致，因此花瓣脱落起点、花托衔接、运动路径、旋转、翻滚、大小、色彩和时长均未改变。
- 连续采样捕获 35 个动态花瓣与非所属牡丹的交叠状态；所有交叠均发生在统一顶层，不再被任何牡丹图片覆盖。
- 浏览器控制台 errors / warnings: 0。
- Vinext production build passed；Node tests 26 / 26 passed；ESLint 0 errors（11 个既有 warning）。
- 未修改确定性排盘、规则版本、前五页或第七页以后内容；本轮未发布。

final result: passed
# 第七页「观卦」与进入动作 QA（2026-07-31）

- 第六页沿用已定稿的牡丹长卷、三数组和落瓣图层；仅在取数区内补入边界确认与“观卦”按钮，不再要求滚动到独立的第五步区块。
- 第七页首屏只呈现卦象、卦名、卦序、卦辞和一句极短引导，不显示用户原问题。
- 第八页及后续解读默认隐藏；只有点击“详细解卦”后才展开，并将焦点移到“本卦、互卦与变卦”。
- “详细解卦”提供 `aria-controls` 与 `aria-expanded`；键盘焦点样式可见；滚动行为遵守 `prefers-reduced-motion`。
- 确定性排盘请求结构、版本与算法未改动；现实信息仍只用于后续个性化解读，不作为卦象证据。
# 成卦页牡丹背景与左对齐修订（2026-08-01）

- 仅修改第六页成卦展示；第 1–5 页、第七页观卦门控和确定性排盘规则未改动。
- “心中再默念一遍所问之事”起的引导、三组取数、范围提示、边界确认与“观卦”按钮统一左对齐。
- `取1-999之间的数字，填入上方文字右侧` 已移到三组取数之后、边界确认之前。
- “观卦”按钮保留八卦标记，移除旧横幅位图形成的矩形图底。
- 新背景 `casting-peony-background-v3.webp` 原位保留与三朵花一一对应的枝干、花托与牡丹叶，仅清除竹、树线、山石、桥船和建筑；宣纸底由暖黄调整为冷灰米白，并继续隔离旧问卦长卷。
- 实际浏览器复核：桌面 1440×900 与手机 390×844 均无横向溢出；三句引导左边线、标题左边线及手机端按钮左边线一致；`prefers-reduced-motion` 仍沿用既有落瓣停用规则。
- 验证：部署构建通过；前端回归 21/21；完整 Python 回归 951/951。
# Design QA — 第三页「正问」静山流云修正 v8（2026-08-01）

## 对照依据

- 用户问题截图：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-5be9f048-c082-4886-af48-6d5be66eeed3.png`。
- 本地实机帧：`qa/inquiry-cloudfall-v8-final2-t1.png`、`qa/inquiry-cloudfall-v8-final2-t2.png`，相隔 3.2 秒。
- 运动差异图：`qa/inquiry-cloudfall-v8-final2-diff-x8.png`。
- Codex in-app Browser：CSS viewport 1280 × 720，devicePixelRatio 1.25，传输截图 1265 × 712，页面 `#inquiry`。

## Findings

- 已移除 v7 中复用整张背景图并移动的 `.inquiry-cloud-sky-drift` 图层；基础山水图和山体遮挡图均无动画，计算样式 `animation-name: none`，固定缩放矩阵在两帧间不变。山峰轮廓和岩石纹理不再发生位移。
- 上方云海只在固定空间遮罩内部缓慢翻涌，不再移动遮罩或底图；速度与亮度起伏已收窄到接近松树、肉眼可感但不抢画面的程度。
- 山顶下泄云改为两条明确路径：一条宽云幕沿主峰左侧下落，一条窄云流穿过右侧山谷。云体使用沿路径推进的暖白半透明体积与向下平流的分形纹理，只有云的透明度和内部纹理变化，山体像素始终静止。
- 动画像素全部采用暖白色，不再用移动的深灰阴影刻画云，因此不会把云的明暗误读为山石纹理平移；山体只会随云遮挡短暂时隐时现。
- 3.2 秒对比中：顶部云海区域平均通道差约 0.25，明显小于松树区域约 4.31；下泄流云区域平均通道差约 1.30，形成肉眼可感的下行变化，同时没有整幅背景位移。
- 页面文字、输入区、四个例句和松树动效均未改变。

## Interaction And Engineering Verification

- 输入“我现在是否应该继续推进这个计划？”后，“写好了，继续辨识”正常启用；清空后恢复初始状态。
- DOM 中 `.inquiry-cloud-sky-drift` 数量为 0；两层 WebGL canvas 均为 1600 × 900，浏览器 console errors 为 0。
- Vinext production build：passed。
- Node rendered/interaction tests：28 / 28 passed。
- ESLint：0 errors；14 个既有 `<img>` / ARIA warnings。
- `git diff --check`：passed。

## Comparison History

1. v7：移动整张背景图的局部重采样层仍含山峰像素，导致用户看到“整座山在动”；顶部云海幅度也过大，判定为 P1。
2. v8 iteration 1：彻底删除整图重采样层，山体恢复完全静止；只保留固定遮罩内的程序云。
3. v8 final：下泄云由平直条带改成沿两条山势路径推进的连续云体，并将所有移动像素改为暖白云雾，增强从峰顶流下来的可读性。

final result: passed

---
# Design QA — 第三页顶部云层原位舒展 v9（2026-08-01）

## 对照依据

- source visual truth：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-a9659138-81ce-4f4d-867a-aee0669a165a.png`（1132 × 271），用户明确指定页头下方的顶部云层。
- 既有动效参照：第五页 `.final-question-sky-drift` 的双层软遮罩、8.4 秒 / 11.8 秒错峰节奏与明暗舒展方式。
- implementation screenshots：`qa/inquiry-cloud-breath-v9-final-t1.png`、`qa/inquiry-cloud-breath-v9-final-t2.png`（1265 × 712），相隔 4.2 秒。
- focused comparison：`qa/inquiry-cloud-breath-v9-final-comparison.png`；源图与实现顶部区域均归一化为 1132 × 271 后同图上下对照。
- motion evidence：`qa/inquiry-cloud-breath-v9-final-diff-x10.png`。
- 浏览器状态：Codex in-app Browser，CSS viewport 1280 × 720，devicePixelRatio 1.25，页面 `#inquiry`，问题为空。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 顶部云层已从“水平流动”改为原位舒展：两层真实水墨底图局部软遮罩只做纵向 6px 内的轻微起伏、1.008–1.020 的缓慢呼吸缩放，以及亮度和透明度渐变；没有横向位移，也没有首尾拼接。
- 动效节奏直接沿用第五页右上落霞的 8.4 秒主层、11.8 秒次层和 -3.2 秒错峰方式，但为云层去掉了落霞的横向 `background-position` 推进，因此视觉是云气在原地张弛，不是流走。
- 动态遮罩集中在顶部左中部云区。4.2 秒对比中，目标云区平均通道差约 1.97；右上山体区域仅约 0.25。山体计算样式仍为 `animation-name: none`，固定矩阵不变。
- 峰顶下泄云仍由唯一的前景 WebGL 层负责，顶部不再挂载旧的后景流动 canvas，避免两种动线互相干扰。

## Required Fidelity Surfaces

- Fonts and typography：未修改；标题、导航、输入及例句字体层级与用户截图一致。
- Spacing and layout rhythm：未修改页面布局、裁切、边距或输入区位置。
- Colors and visual tokens：沿用宣纸米白、淡墨与既有图片色阶；呼吸层只调整真实云图的亮度、对比度和透明度。
- Image quality and asset fidelity：继续使用 `question-cloudfall-base-v6.png` 的真实水墨云纹，没有 CSS 绘制云朵、占位图或新造山体像素。
- Copy and content：页面文案完全未改。

## Interaction And Engineering Verification

- `.inquiry-cloud-breath` 数量为 1；主层动画 `inquiry-cloud-breathe-near` 为 8.4 秒，次层 `inquiry-cloud-breathe-soft` 为 11.8 秒。
- 页面只保留一个前景流云 canvas；山体动画为 `none`。
- 输入测试问题后，“写好了，继续辨识”正常启用；清空后恢复。
- 浏览器 console errors：0。
- Vinext production build：passed。
- Node rendered/interaction tests：28 / 28 passed。
- ESLint：0 errors；14 个既有 `<img>` / ARIA warnings。
- `git diff --check`：passed。

## Comparison History

1. v8：顶部云海使用程序纹理缓慢横向推进，虽然幅度较小，但不符合用户本轮提出的“像落霞一样原位动，而不是流动”。
2. v9 iteration 1：改用第五页双层软遮罩节奏，初版云区变化可测但肉眼偏弱，记录为 P2。
3. v9 final：扩大明暗舒展范围和纵向呼吸幅度，同时保持横向位移为 0；目标云区变化提升约一倍，右上山体仍近乎静止。

final result: passed

---
# Design QA — 第三页顶部云层肉眼可见增强 v10（2026-08-01）

## 对照依据

- source visual truth：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-a9659138-81ce-4f4d-867a-aee0669a165a.png`（1132 × 271），用户指定页头下方顶部云区。
- implementation screenshots：`qa/inquiry-cloud-breath-v10-visible-t1.png`、`qa/inquiry-cloud-breath-v10-visible-t2.png`（1265 × 712），相隔 4.2 秒。
- focused comparison：`qa/inquiry-cloud-breath-v10-visible-comparison.png`，源图与实现顶部区域归一化为 1132 × 271 后同图对照。
- motion evidence：`qa/inquiry-cloud-breath-v10-visible-diff-x7.png`。
- 浏览器状态：Codex in-app Browser，CSS viewport 1280 × 720，devicePixelRatio 1.25，`#inquiry`，问题为空，`prefers-reduced-motion: false`。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- v9 的技术动画虽运行，但两帧平均变化不足以让用户肉眼识别，按用户反馈重新定级为 P1，而不是继续视作已完成。
- v10 将第五页落霞的可见明暗跨度和舒展幅度真正迁移到顶部云层：主层透明度在 .32–.68 之间变化，缩放 1.018–1.040，纵向起伏 13px；次层以 11.8 秒错峰补充较慢的张弛。所有水平位移仍为 0，因此不是横向流云。
- 4.2 秒两帧中，目标顶部云区平均通道差约 3.73，较 v9 的约 1.97 提升近一倍；实际并列帧中，左上至中部云纹的聚散和明暗已经能直接看出。
- 右上山体区域平均通道差仅约 0.28；山体计算样式保持 `animation-name: none` 和固定矩阵，增强没有扩散到山峰。

## Required Fidelity Surfaces

- Fonts and typography：未改。
- Spacing and layout rhythm：未改页面布局、裁切或输入区域。
- Colors and visual tokens：仍为宣纸米白与淡墨，仅提高顶部真实云纹图层的局部对比和亮度呼吸。
- Image quality and asset fidelity：继续复用 `question-cloudfall-base-v6.png` 的真实水墨云纹，软遮罩边缘无矩形或接缝。
- Copy and content：未改。

## Interaction And Engineering Verification

- 浏览器确认主动画 `inquiry-cloud-breathe-near` 正在以 8.4 秒运行，系统未启用减少动态效果。
- 山体 `animation-name: none`；输入测试问题后，“写好了，继续辨识”正常启用。
- 浏览器 console errors：0。
- Vinext production build：passed。
- Node rendered/interaction tests：28 / 28 passed。
- ESLint：0 errors；14 个既有 warnings。
- `git diff --check`：passed。

## Comparison History

1. v9：动画范围正确、山体静止，但肉眼可见度不足；用户实际检查后仍看不出改变，判定为 P1。
2. v10：按第五页落霞的真实幅度增强透明度、缩放、纵向张弛和局部对比；两帧可见差异近乎翻倍，且山峰区域仍近乎静止。

final result: passed

---
## 第六页至第七页修复（第 37 版）

- 提前结束辨识时，只依据用户原问题与已经回答的文字补齐有限分类字段；不补写事实，不把问题文字用于确定性排盘。
- 提前结束路径只调用确定性 V3 排盘并直接进入第七页，不再因个性化解读所需的事实与未知项为空而拦截“观卦”。
- 成卦背景按问卦容器左右内边距差值反向校正，桌面端宣纸与牡丹场景铺至视口左缘；手机端偏移归零。
## 第六页成卦收束复检（第 42 版）

- 以第 41 版线上源码为底稿，仅收束第六页；第 1–5 页与第七页结果过渡保持不变。
- 第六页继续使用已确认的 `casting-peony-background-v3.webp`、三组花托枝叶、三朵牡丹和独立顶层落瓣动画；没有替换或重绘花朵与花瓣。
- 删除重复的边界确认、八卦标记和第二组加载提示。页面只保留一个“成卦”按钮；提交后原位显示“正在成卦”，完成排盘后沿用既有过渡自动进入第七页。
- “取1-999之间的数字，填入上方文字右侧”位于三组取数下方；按钮移除横幅伪元素，保持透明、无图片外缘。
- 桌面 1440×900 与手机 390×844 实机验证：背景与宣纸底完整覆盖视口，无横向溢出或左右竖向接缝；三组输入、提示和按钮均保持入画。

# 第六页「成卦」太极八卦图标微调（Sites v44）

- 仅在「成卦」文字左侧复用此前「观卦」所用的 `BaguaMark`，未改动图标素材与页面其余内容。
- 桌面端图标为 30px，手机端为 28px；沿用按钮的 flex 对齐和间距，保持文字与图标垂直居中。
- 第六页按钮的背景伪元素仍关闭，避免重新出现图片边缘；第七页保持不变。

# 第五页至第七页「一页一屏」边界修复（Sites v45）

- 复测 1896×922 视口后确认：第六页本体高度原本已等于视口减去 68px 固定页头；多出的空段来自外层 `inquiry` 的底部内边距，以及结果尚未生成时提前占位的说明与页脚。
- 第六页出现后，外层底部内边距归零；结果说明和站点页脚只在第七页结果生成后出现，使第六页末端与第七页起点直接相接。
- 第五页进入第六页改为一次性定位，并在不触发二次滚动的前提下把焦点交给「成卦」标题，避免平滑滚动与动态内容插入叠加造成上下跳动。
- 新增可复用的 `viewport-page` 页面约束：桌面为 `100svh - 68px`，手机为 `100svh - 58px`。第五页、第六页和第七页首屏已接入；后续第八至第十页及观事簿设计沿用这一规则。
