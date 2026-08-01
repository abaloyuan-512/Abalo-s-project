# Design QA — 第 3 页「正问」电影感无缝云河 v3

## 比较目标

- Source visual truth：`qa/question-motion-v2-desktop-final.png`，结合用户本轮明确要求：云层不再往返平移；始终由左向右；无图片边缘；具备流水、翻涌、穿山、绕山与山前山后景深；背景铺满视口。
- Implementation：`qa/question-cloud-stream-v3-desktop-final.png`，1440 × 900 CSS px，device scale 1；与 v2 源图同尺寸、同一第三页空白输入状态。
- Mobile：`qa/question-cloud-stream-v3-mobile.png`，390 × 844 CSS px，device scale 1。
- Full-view comparison：`qa/question-cloud-v2-vs-v3.jpg`。
- Focused motion comparison：`qa/question-cloud-stream-v3-motion-comparison.jpg`，两帧间隔 4.2 秒；云河的横向位移、纵向起伏、透明度与尺度变化均可见，因此无需额外裁切局部图。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与文案：沿用已审定的毛草标题、楷体正文、朱砂小标题及全部第三页文案；字号、行距、字重与换行未改变。
- 间距与布局：表单网格、标题、输入区和四个例句位置未漂移。场景层改为以视口中心定位的 `100vw` 满框画布；1440 px 桌面与 390 px 手机均无横向溢出，背景不再在右侧留白。
- 色彩与视觉令牌：继续使用暖宣纸、淡墨、朱砂与低对比宋画体系；新云河经暖灰化处理，没有品红色键残留。
- 图像质量：`question-cloud-stream-v3-tile.png` 为真实水墨位图。左右首尾像素 RGBA 完全一致，edge mean diff 为 0；透明边缘无矩形框、硬切线或明显接缝。`question-mountain-occluder-v3.png` 直接从同一底板提取，透视与山体位置一致。
- 动效与景深：远云位于山体遮挡层之后，近云位于其前；山峰会切开远云，近云从低处掠过，形成穿谷、绕峰和山前山后的层次。两层均持续由左向右循环，不再使用 `alternate` 往返动画。31 秒远云与 19 秒近云存在不同流速，并通过纵向起伏和短暂尺度变化形成浪头与涟漪。
- Copy：未新增解释性文字或视觉标签，页面任务仍只聚焦“正问”。
- 响应式：手机端把无缝周期扩大为 760 px，避免小屏将云河压缩成细带；松树继续隐藏以保证表单可读，云河仍持续流动。
- 无障碍与交互：`prefers-reduced-motion: reduce` 下云河和松树动画停止，静态画面完整保留；表单、例句、继续按钮与键盘焦点语义未改变。
- 浏览器控制台：0 warning / 0 error。

## Comparison history

### 第一轮（v2）

- [P1] 云层以矩形图片在画面内往返移动，方向会反转，无法形成持续流水感；边缘进入视口时可见。
- [P2] 云与山体处于同一前后关系，缺少穿山、绕山、被山峰分流的景深。
- [P2] 背景场景按父容器边界铺设，用户观察到右侧存在明显空白。

### 修复后（v3）

- 生成横贯画面的流线型水墨云河，并对左右边缘进行周期融合；CSS 以与纹理同宽的周期连续向右推进，循环点等价且无跳变。
- 新增前景山体遮挡层，DOM 顺序为“底板 → 远云 → 山体 → 近云 → 松树”，在同一幅画中形成真实遮挡关系。
- 场景改为视口中心的满框画布，底板额外放大 1.2% 消除亚像素边缘；桌面和手机实测均无横向溢出。
- 4.2 秒 A/B 帧 mean absolute pixel difference 为 2.421，变化覆盖主体画面；实际 `background-position` 始终沿单方向递增，并在周期端点以等价纹理位置无缝复位。

## 工程验证

- `vinext build`：通过。
- Node tests：23 / 23 通过。
- Python 资产脚本语法检查：通过。
- ESLint：0 error / 19 个既有 `<img>` warning。
- 未修改确定性排盘、规则版本、AI 辨识逻辑或旧版入口。

final result: passed

---

# Design QA — 第 3 页「正问」云海与松树本体动效 v2

## 用户问题与修正结果

- Source visual truth：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-3a96a5b8-3bcd-44d7-8472-2289d78fbb3f.png`。
- 已删除「正问」下方的“写下一件真实具体的事”，页面与服务端渲染均不再包含该句。
- 原先含松树的静态底图拆为三部分：无松树山水底板、两层云海、完整松树本体。底板不再保留静态松树，因此不会形成影子或双重树影。
- 云海使用两层真实水墨 PNG，分别以 28 秒和 18 秒周期进行反向横移、缩放、起伏和透明度变化；3.2 秒对照帧的 mean absolute pixel difference 为 2.446，变化覆盖画面主体区域。
- 松树本体以左下根部为固定轴，6.8 秒周期在约 -0.22° 至 +0.38° 之间轻摆，并带极小的倾斜与位移；实际 DOM transform 在 3.2 秒内发生变化。

## 视觉对照与浏览器验证

- Desktop final：`qa/question-motion-v2-desktop-final.png`，1440 × 900 CSS px。
- Mobile final：`qa/question-motion-v2-mobile.png`，390 × 844 CSS px，无横向溢出。
- 用户截图与修正版并排：`qa/question-user-defect-vs-v2.jpg`。
- 动效 A/B 帧并排：`qa/question-motion-v2-comparison.jpg`，两帧间隔 3.2 秒。
- 桌面端：副标题已移除；松树不遮挡「正问」；云海可见且持续翻涌；正文、输入区与四个例句保持可读。
- 移动端：隐藏松树本体以避免压字，保留云海流动；副标题不存在；页面无横向溢出。
- `prefers-reduced-motion: reduce` 下停止云海与松树动画，保留完整静态画面。
- 浏览器控制台：0 warning / 0 error。

## 工程验证

- `vinext build`：通过。
- Node tests：23 / 23 通过。
- ESLint：0 error / 20 个既有 `<img>` warning，不阻断。
- 未修改确定性排盘、规则版本、AI 辨识逻辑或旧版入口。

final result: passed

---

# Design QA — 第 2 页「明法」河道内部流场 v8

## 比较目标与证据

- Source visual truth：`qa/method-river-desktop-final-v7.png`，1425 × 891 px；该版本的山河底图色调、三句经文、右侧引导和底部 CTA 均为用户明确要求冻结的视觉真值，仅旧的 S 形覆盖层运动未通过用户验收。
- Rendered implementation：`qa/method-river-desktop-final-v8.png`，1425 × 891 px；浏览器 CSS 视口 1440 × 900，默认状态，桌面背景使用 `method-river-wide-v1.webp`。
- Mobile implementation：`qa/method-river-mobile-flow-a-v8.png` 与 `qa/method-river-mobile-flow-b-v8.png`，375 × 811 px；浏览器 CSS 视口 390 × 844，手机背景使用 `method-river-mobile-v1.webp`。
- Full-view combined comparison：`qa/method-river-background-comparison-v7-v8.png`。源图与实现先保持相同 1425 × 891 捕获尺寸，再等比缩小 50% 后并排；无设备框或不同密度干扰。
- Motion comparison：`qa/method-river-motion-comparison-v8.png`；两张桌面帧间隔 1.05 秒。Focused region：`qa/method-river-motion-focus-v8.png`，聚焦中央河道、两侧山体、两组文字与 CTA，用于辨别水面内部位移和岸线稳定性。
- 状态：第二页默认态，背景已加载，WebGL canvas 为 `method-river-flow is-ready`；首屏文字与 CTA 均未被操作。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与文字：三句经文继续使用用户确认的 `Liu Jian Mao Cao Local` 毛草字体、字号、行距与错落；右侧引导、出处和“开始正问”未改文案、字重、位置或交互。
- 间距与构图：左右山体、中央大江、两组文字与底部 CTA 的网格和留白未变。v7 与 v8 同尺寸并排中，主要区域比例和元素对齐一致。
- 色彩与视觉 token：继续使用 `.74` 透明度以及 `brightness(1.12) contrast(.68) saturate(.46)`；没有改动用户已确认的群山深浅、暖宣纸、墨色或朱砂。
- 图像质量：继续采样已审定的桌面/手机真实水墨底图。旧的 `method-river-current-flow-v2.png` 不再渲染，因而没有整张透明 S 形纹理反复掠过的贴图感、色键边缘或双层水纹叠影。
- 动效：河道中心线和岸界保持固定；河内使用宽流、横向剪切、细碎急纹三种尺度，近景速度和位移高于远景，浪脊亮纹在流场中生成与消散。桌面两帧中央河区 mean absolute pixel difference 为 3.158，左岸为 0，右侧边缘为 0.207；手机中央河区为 2.906，两侧边缘分别为 0 与 0.014，变化集中在河道内部而非整张画面。
- 性能与降级：像素密度上限为 1.5，离开视口或页面隐藏时停止实际绘制；WebGL/贴图加载失败时保留原静态 `picture`；`prefers-reduced-motion: reduce` 下不启动流场并隐藏 canvas，静态山河与全部内容保持可用。
- 响应式与交互：1440 × 900、1920 × 1080 与 390 × 844 均无横向溢出、遮挡或岸线裁切异常。第二页原有鼠标、触屏、键盘、逐字书写和准备确认逻辑未改。
- 浏览器控制台：页面 warning 0 / error 0。

## Comparison history

### v7 用户验收结论

- [P1] 两张 S 形透明水纹作为整层图片做位移与缩放，画面像线条覆盖层来回滚动，没有“水在河道里面流”的空间感。
- [P2] 水面不同尺度、不同速度和近岸减速缺失，导致运动规律过于一致，视觉上显假。

### v8 修复

- 删除 v7 两层 `method-river-current` DOM 与两组整图平移动画。
- 新增以原山河底图为纹理的河道内部流场：固定河道遮罩、沿弯曲中心线的下游方向、多尺度噪声位移、岸边渐隐、远慢近快、局部浪脊明暗。
- 保持静态底图作为无 WebGL 与减少动态效果时的完整回退，不改变文字、排版、CTA、背景滤镜和页面流程。

### 修复后证据

- `qa/method-river-background-comparison-v7-v8.png`：冻结的文字、构图和背景色调保持一致。
- `qa/method-river-motion-focus-v8.png`：1.05 秒前后山体与岸线稳定，中央河道的水纹局部发生不同方向和不同幅度的变化，不再是整条 S 形图层平移。
- `qa/method-river-mobile-flow-a-v8.png` / `qa/method-river-mobile-flow-b-v8.png`：窄屏仍使用竖版山河底图，流动集中于中央水道，没有压住文字或破坏首屏阅读。

## 工程验证

- `vinext build`：通过。
- 第二页定向测试：1 / 1 通过；新增校验流场组件、下游位移、岸边渐隐、旧 S 形资产不再引用、静态回退与 `prefers-reduced-motion`。
- 完整 Node 测试：21 / 23 通过；两项失败均来自本轮未修改的第 3 页云海实现与现有测试契约不一致（仍在期待 `question-cloud-stream-v3-tile.png` 与旧 `background-position` 规则），未扩大范围修改第 3 页。
- ESLint：0 error，19 个项目既有 `<img>` 优化 warning。
- 未修改首页、第二页冻结文字与布局、确定性排盘规则、AI/排盘边界或旧版入口；未部署、未提交、未推送。

final result: passed

---

# Design QA — 第 2 页「明法」山色统一与江流增强 v7

## 比较目标与证据

- Source visual truth：用户对 v6 浏览器实景的两项明确反馈——两岸群山颜色过深、中央江河的奔流动效不可感知。
- 调整前：`qa/method-river-before-feedback-v7.png`，1440 × 900 CSS px，devicePixelRatio 1。
- 最终桌面：`qa/method-river-desktop-final-v7.png`；连续动效帧为 `qa/method-river-desktop-final-flow-1-v7.png` 与 `qa/method-river-desktop-final-flow-2-v7.png`，帧间隔 1.9 秒。
- 最终手机：`qa/method-river-mobile-feedback-a-v7.png` 与 `qa/method-river-mobile-feedback-b-v7.png`，390 × 844 CSS px，帧间隔 1.8 秒，无横向溢出。
- 同屏比较：`qa/method-river-feedback-comparison-v7.png`，将调整前与两张调整后连续帧分别归一为 480 × 300 px 后并排；没有浏览器框、密度或裁切差异。
- 聚焦比较不另设裁切：本轮仅改变全屏底图色阶与贯穿中央的大面积江流，关键差异在全屏比较和连续帧中已经清晰可见；文字、CTA 和局部控件没有改动。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与文案：三句经文、右侧引导、引文出处与 CTA 的字体、字号、字重、行距、位置和内容均未改动。
- 间距与布局：双栏比例、纵向节奏、底部 CTA 位置保持 v6；1440 × 900 与 390 × 844 均无遮挡、裁切或横向溢出。
- 颜色与令牌：第二页底色改用全站 `var(--paper)`；山河底图应用 0.74 透明度、1.12 亮度、0.68 对比度与 0.46 饱和度，消除两侧山峰过黑的问题，回到其他页面的暖宣纸淡墨层级。前景大字仍保持深墨，不因背景洗淡而减弱。
- 图像质量：新增 `public/method-river-current-flow-v2.png`，为 1672 × 941 RGBA 透明真实水墨浪纹资产；透明边角、江道透视、飞白水沫与回旋纹理均已检查，无绿色边缘、硬裁切多边形、山体重影或占位图形。
- 江流动效：两层浪纹沿中央 S 形江道持续向前景平移并缓慢放大，周期同为 7.6 秒、相位错开半周。12 组连续采样中两层透明度总和最低 0.332、最高 0.498，不再出现两层同时消失的静止空档；连续帧可见浪峰位置发生明显变化。
- 响应式：手机使用同一透明浪纹的中央裁切，江面贯穿画面但不覆盖标题可读性；手机背景山色同步洗淡。
- 无障碍：`prefers-reduced-motion: reduce` 下 `.method-river-motion` 完全隐藏，保留洗淡后的静态山河；按钮、焦点、两倍书写和进入正问的状态确认均未改变。
- 浏览器控制台：0 warning / 0 error。

## Comparison history

### 第一轮

- [P1] 原动效仅移动整张底图 5–10px，峰值透明度约 0.14–0.20，肉眼几乎无法感知。
- [P2] 原底图两岸山峰与其他页面相比对比度过高，尤其左右边缘形成过重的黑色压迫。

### 中间尝试

- 将整张底图的位移与透明度直接放大后，浏览器帧出现明亮的多边形裁切边界。该方案判定为不合格并完全移除，没有保留到最终实现。

### 最终修复

- 使用内置图像生成制作独立江流浪纹，在绿色色键移除后得到透明 PNG；动画只推动浪纹，不再移动或裁切山体。
- 两层浪纹使用固定半周错相，保证一层淡出时另一层处于可见阶段；运动方向由远处中央持续向下游前景推进。
- 底图改为全站纸色并降低山体对比度与饱和度。

### 修复后证据

- `qa/method-river-feedback-comparison-v7.png` 中，调整后的两侧群山明显比调整前更轻，且不影响文字层级。
- `qa/method-river-desktop-final-flow-1-v7.png` 与 `qa/method-river-desktop-final-flow-2-v7.png` 中，江面飞白与浪峰沿江道发生可见位移；没有硬边、矩形蒙版或山体重影。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：23 / 23 通过。
- ESLint：0 error；20 个项目既有 `<img>` 优化 warning，本轮未新增 warning。
- 未修改第 1 页、文字排版、确定性排盘规则、AI 边界或旧版入口；未部署、未提交、未推送。

final result: passed

---

# Design QA — 第 3 页「正问」松下云海动效 v1

## 比较目标

- Source visual truth：`C:\Users\27622\.codex\generated_images\019fa5e9-2a61-7f92-813b-b9d609ccb12c\exec-09dafc46-1b09-433c-808f-de3f8ef4d27f.png`，即用户选定的第二张“孤松与云海”背景。
- Desktop implementation：`qa/question-cloud-motion-desktop-final.png`，1440 × 900 CSS px，1× 密度，第三页空白输入态。
- Mobile implementation：`qa/question-cloud-motion-mobile-v2.png`，390 × 844 CSS px；浏览器内容区 375 px，无横向溢出。
- Full-view combined comparison：`qa/question-source-vs-implementation-v1.jpg`。源图按居中裁切归一到 1440 × 900 后，与同尺寸实现并排比较。
- Motion comparison：`qa/question-cloud-motion-comparison-v1.jpg`，两个桌面帧间隔 3.2 秒；同时读取远云、近云与松枝图层的实际 transform，三者均发生变化。
- State：第 2 页确认后进入第 3 页；顶部导航、问题输入、四个例句和继续按钮保持原有功能。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与文案：沿用现有毛笔标题、楷体正文、朱砂小标题和全部已确认文案，没有因背景替换改变字号、字重、行距或输入流程。
- 布局与留白：桌面端孤松稳定落在左下，标题位于松冠上方，右侧输入与四个例句都落在云海留白区；1440 × 900 无遮挡或横向溢出。移动端改为居中裁切，并关闭额外松枝叠层，避免枝叶穿过例句文字。
- 色彩与资产：选定原画转换为 92 质量 WebP，背景为 140,990 bytes；云海透明层 644,248 bytes；松枝透明层 199,298 bytes。三张资源保持暖宣纸、浅墨远山和宋画低对比体系，没有拉伸、硬边或循环接缝。
- 云海动效：远云 34 秒、近云 21 秒，方向、位移和透明度不同，形成持续但克制的横向流动与轻微起伏；图层使用真实水墨纹理而不是渐变或程序绘制。
- 松树动效：仅松冠透明层以 8.6 秒周期做约 0.12° 的微摆和不足 2px 的位移，树干、根部与山石保持静止，不产生整棵树漂浮感。手机端出于可读性关闭额外松冠动画，仍保留云海流动。
- 无障碍：`prefers-reduced-motion: reduce` 下远云、近云和松枝全部停止；静态背景仍完整呈现。装饰图层均从无障碍树隐藏，不影响表单语义和键盘操作。
- 交互验证：实际点击“进入观象之法”与“开始正问”；输入具体问题后“写好了，继续辨识”可用，随后清空恢复初始态。浏览器控制台 0 warning / 0 error。
- 聚焦区域比较：以 motion frame A / B 检查云海底部和松冠边缘；实际 CSS transform 在 3.2 秒内发生变化，画面没有跳帧、闪白或明显重影。

## Comparison history

### 第一轮

- [P2] 390 × 844 下左侧松冠进入例句区域，部分枝叶压住第三、第四个例句，降低小字号可读性。
- 修复：手机断点把背景焦点从 24% 调整到居中，并关闭额外松冠叠层；保留基础原画的极少量枝梢和两层云海动画。

### 修复后

- `qa/question-cloud-motion-mobile-v2.png` 中四个例句均落在干净宣纸与浅雾上，无枝叶穿字；页面宽度与内容宽度一致。
- 桌面端复核仍保留完整孤松与松冠微摆，背景和界面布局未漂移。

## 工程验证

- `vinext build`：通过。
- Node tests：23 / 23 通过，新增云海、松枝资源和 reduced-motion 断言。
- ESLint：0 error；21 个 `<img>` 与既有 ARIA 规则 warning，无阻断错误。
- 未修改确定性排盘引擎、规则版本、AI 辨识逻辑、旧版入口或第 1、2 页流程。

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

# Design QA — 第 2 页「明法」大山大河动态背景 v6

## 比较目标与证据

- Source visual truth：`C:\Users\27622\.codex\generated_images\019f9e9b-9c3e-7820-ba92-7978b3aa47d0\exec-63f7ffcf-8e5a-44d1-a118-d00b475c8927.png`，即用户确认的第一张“大山大河、中央奔流”视觉稿，1634 × 963 px。
- 最终桌面实现：`qa/method-river-desktop-reference-size-v5-final-2.png`，1634 × 963 CSS px，devicePixelRatio 1，默认状态。
- 最终手机实现：`qa/method-river-mobile-v5-final-2.png`，390 × 844 CSS px，devicePixelRatio 1，默认状态；浏览器内容宽 375 px，无横向溢出。
- 第一轮并排比较：`qa/method-river-comparison-v5.png`。
- 修正后并排比较：`qa/method-river-comparison-v5-final.png`。源稿与实现均归一为 817 × 482 px 后并排，比较时没有设备框、浏览器栏或密度差异。
- 书写状态：`qa/method-river-desktop-writing-v5.png` 与 `qa/method-river-desktop-writing-end-v5.png`；实测点击后整句严格 `scale(2)`，逐字墨迹完成后保持深墨。
- 本轮全屏比较中三句大字、右侧两段引导、底部 CTA 与墨痕均清晰可辨，因此不需要额外裁切的聚焦比较。江流动效另以 DOM 计算样式在间隔 1.4 秒的两帧中验证位移、缩放和透明度均发生变化。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与层级：左侧继续使用已确认的 `Liu Jian Mao Cao Local` 飘逸毛笔字体，三句无标点；桌面字号提升为 `clamp(86px, 7vw, 112px)`，行间距为 `.56em`，第二句向右错落。默认墨色增深，但悬停/键盘焦点的 `scale(1.34)`、700 字重和点击后的两倍逐字书写均保留。右侧沿用既定文案与较轻层级，CTA 缩为 17–19px 毛笔字。
- 间距与构图：桌面网格调整为 `1.45fr / .85fr`，右侧引导从过远的山脚区域收回中央江面一侧；左侧整体微上移 14px。底部“开始正问”继续与首页入口同轴，真实墨色水势图取代直线或白色浪花。
- 颜色：使用暖宣纸、墨黑、淡墨和既有朱砂变量；没有加入现代卡片、发光或高饱和色。左侧标志性经文的分量高于右侧说明，符合“左重右轻”。
- 图像质量：桌面和手机分别使用真实生成的 WebP 山河资产，构图为两岸重山与中央蜿蜒大江，无船、人物、楼阁；没有拉伸、透明边缘或硬切。江流运动使用同一真实水墨资产的两层局部纹理，而非 CSS 绘画或占位形状。
- 文案：仅保留“接下来 / 我们尝试观象”“请闭上眼睛 / 做三个呼吸”“开始正问”；没有“约三分钟”、阶段编号、输入框、AI 辨识或成卦内容。
- 响应式：1634 × 963、1440 × 900 与 390 × 844 均无横向溢出、遮挡或 CTA 裁切；手机自动采用纵向山谷素材与单列阅读顺序。
- 交互与无障碍：三句均为原生按钮并保留 Pointer、键盘焦点和触屏点击语义；“开始正问”实测 `aria-pressed=false → true`、第 3 页 `hidden=true → false`，焦点落到 `#inquiry-title`。`prefers-reduced-motion` 下关闭江流、入场、书写和过渡动画，静态背景和完整文字仍可见。
- 浏览器控制台：页面 warning 0 / error 0。

## Comparison history

### 第一轮

- [P2] 左侧三句在浏览器实现中比确认稿更浅、更小，未充分形成用户要求的“左重右轻”。
- [P2] 右侧说明起点约比确认稿向右偏移 90px，中央留白仍略显松散。

### 修复

- 将经文桌面上限从 100px 提升到 112px，默认墨色由双重低透明调整为接近实墨；三句仍保留被选中时其余两句退墨的状态差异。
- 重分桌面双栏比例并把栏间距收至 `clamp(72px, 7vw, 120px)`，右侧文字回到确认稿中的江岸位置。

### 修复后证据

- `qa/method-river-comparison-v5-final.png` 中，三句字号、墨色分量、右侧起点与底部 CTA 的视觉关系已与确认稿一致；字体字形差异来自用户已确认并要求保留的本地毛草字体，属于有意产品约束。
- `qa/method-river-mobile-v5-final-2.png` 中三句、引文、两段引导和 CTA 全部处于首屏，文字未压住山峰边缘，页面无横向溢出。

## 工程验证

- `vinext build`：通过。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：23 / 23 通过。
- ESLint：0 error；仅保留项目既有 20 个 `<img>` 优化 warning，本轮新增的 `picture aria-hidden` warning 已修复。
- 未修改第 1 页首页、确定性排盘规则、AI/排盘边界、旧版入口；未部署、未提交、未推送。

final result: passed
# Design QA — 首页「梅枝引蝶」开场与首页定稿 v12

## Comparison target

- Source visual truth: `public/hero-entry-wide-v7.webp`（1774 × 887 px）与用户落点参考 `C:\Users\27622\AppData\Local\Temp\codex-clipboard-bcad3d84-9c19-451d-b978-7951a2138afa.png`（495 × 252 px）。
- Rendered implementation: `qa/entry-v12-desktop-final.png`（1440 × 900 px）、`qa/entry-v12-square-final.png`（1024 × 1024 px）、`qa/entry-v12-mobile-final.png`（390 × 844 px）。
- Full-view combined comparison: `qa/entry-v12-source-vs-implementation.png`。左侧源图按实现相同的 cover 尺寸与 42% 水平焦点归一到 1440 × 900；右侧为 1440 × 900 浏览器截图。CSS viewport 1440 × 900，devicePixelRatio 1。
- Focused comparison: `qa/entry-v12-landing-focus-comparison.png`。左侧为用户指定的「象」字右侧飞白落点，右侧为实现中同一区域，已归一到 495 × 252 px。
- State: 开场完成、梅枝完全隐去、首页常驻元素与循环飞鸟已进入最终状态。另检查开场飞行、停枝与揭幕节点：`qa/entry-v12-opening-flight.png`、`qa/entry-v12-opening-perch.png`、`qa/entry-v12-opening-ripple.png`、`qa/entry-v12-opening-reveal.png`。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 字体与文字：红印内容为「袁帅」小篆视觉，放在竖排题签上方；「寂然不动，感而遂通天下之故。」已改为独立水墨行书资产。文字未被浏览器字体替换、换行或截断。
- 间距与构图：桌面 1440 × 900、方屏 1024 × 1024 与手机 390 × 844 均保持题字、题签、山水、题句、古琴、小舟与箭头的主次关系。桌面 cover 焦点改为 42%，让题签和姓名印完整留在画内；手机上下余量由同源山水模糊铺底，不再出现黑色断层。
- 色彩与质感：全程维持墨黑、暖宣纸、淡墨与少量朱砂。开场从墨黑进入，梅花和落瓣只承担朱砂点睛；主页没有新增现代卡片、边框或发光效果。
- 图像质量：梅枝、蝴蝶、古琴、姓名印、行书与花瓣均为真实生成的位图资产，没有 CSS 绘图或占位形状。古琴素材已裁去透明留白，提高无边框状态下的辨识度；WebP 资源未发现拉伸、透明边缘或明显压缩伪影。
- 文案与功能：删除「了解观象之法」可见文字，保留小舟与下箭头；古琴点击后实测 `aria-pressed=false → true` 且音频播放，再次点击回到 `false` 并暂停。小舟入口为唯一原生按钮并触发向第二屏平滑下滑。
- 动效：蝴蝶飞行约三秒，飞行终点与停枝剪影共用「象」字右侧飞白落点；停枝后水墨波纹扩散并揭出主页。主页完全显现后梅枝才退场。双飞鸟群相差半个周期重叠，前一群淡出时后一群已进入，避免整群消失后的空窗。
- 浏览器控制台已检查。页面功能没有可复现的运行时错误；自动化桥产生的 Statsig 外部遥测超时与开发模式下的通用 `Object` 日志不属于页面代码或交互失败。

## Comparison history

### 第一轮

- [P2] 390 × 844 竖屏使用 contain 构图时，画面上下露出黑色底层；姓名印和古琴落在黑色区域。
- [P2] 梅枝在主页完全显现前已经开始淡出，与用户确认的叙事顺序不一致。
- [P2] 1440 × 900 的 cover 居中裁切压住左侧题签，姓名印也没有落在题签正上方；古琴透明留白过大，显示后像一小段墨条。

### 修复与复核

- 手机端增加同源山水的模糊铺底，并把姓名印、古琴调整到有效画幅；复核截图中不再有黑色断层。
- 延长梅枝故事线至 7.3 秒，保持到主页背景完成揭示后再退场；题签、行书、古琴、小舟与飞鸟在 6 秒后依次接管画面。
- 桌面图片焦点移至 42%，姓名印使用随视口比例变化的 clamp 位置；古琴裁掉透明外边并复核点击状态。
- 修复后重新捕获桌面、方屏、手机和聚焦区域证据；未发现新的 P0 / P1 / P2。

## Engineering verification

- `vinext build`: passed。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`: 23 / 23 passed。
- ESLint: 0 errors；20 个既有 `<img>` 优化 warnings。
- 未修改确定性排盘、规则版本、AI/排盘边界或旧版入口；未部署、未提交、未推送。

final result: passed

---
# Design QA — 第 3 页「正问」云海与松树本体动效 v2

## 用户问题与修正结果

- Source visual truth：`C:\Users\27622\AppData\Local\Temp\codex-clipboard-3a96a5b8-3bcd-44d7-8472-2289d78fbb3f.png`。
- 已删除「正问」下方的“写下一件真实具体的事”，页面与服务端渲染均不再包含该句。
- 原先含松树的静态底图拆为三部分：无松树山水底板、两层云海、完整松树本体。底板不再保留静态松树，因此不会形成影子或双重树影。
- 云海使用两层真实水墨 PNG，分别以 28 秒和 18 秒周期进行反向横移、缩放、起伏和透明度变化；3.2 秒对照帧的 mean absolute pixel difference 为 2.446，变化覆盖画面主体区域。
- 松树本体以左下根部为固定轴，6.8 秒周期在约 -0.22° 至 +0.38° 之间轻摆，并带极小的倾斜与位移；实际 DOM transform 在 3.2 秒内发生变化。

## 视觉对照与浏览器验证

- Desktop final：`qa/question-motion-v2-desktop-final.png`，1440 × 900 CSS px。
- Mobile final：`qa/question-motion-v2-mobile.png`，390 × 844 CSS px，无横向溢出。
- 用户截图与修正版并排：`qa/question-user-defect-vs-v2.jpg`。
- 动效 A/B 帧并排：`qa/question-motion-v2-comparison.jpg`，两帧间隔 3.2 秒。
- 桌面端：副标题已移除；松树不遮挡「正问」；云海可见且持续翻涌；正文、输入区与四个例句保持可读。
- 移动端：隐藏松树本体以避免压字，保留云海流动；副标题不存在；页面无横向溢出。
- `prefers-reduced-motion: reduce` 下停止云海与松树动画，保留完整静态画面。
- 浏览器控制台：0 warning / 0 error。

## 工程验证

- `vinext build`：通过。
- Node tests：23 / 23 通过。
- ESLint：0 error（既有 warning 不阻断）。
- 未修改确定性排盘、规则版本、AI 辨识逻辑或旧版入口。

final result: passed

---
# Design QA — 第 2 页「明法」奔腾急流 v10

## 本轮目标与视觉证据

- 用户冻结范围：山色、群山构图、左右文字、经典书写交互与底部「开始正问」均不改；只把“平静湖面”提升为大河急流。
- 对照基准：`qa/method-river-desktop-final-v8.png`，即用户已认可色调与整体构图、但认为水面过于平静的版本。
- 最终桌面连续帧：`qa/method-river-rapids-desktop-final-a-v10.png`、`qa/method-river-rapids-desktop-final-b-v10.png`，浏览器视口覆盖 1440 × 900，实际截图 1425 × 891 px，两帧间隔 0.9 秒。
- 最终手机：`qa/method-river-rapids-mobile-final-v10.png`，视口覆盖 390 × 844，实际截图 375 × 811 px。
- 同尺寸并排对照：`qa/method-river-rapids-final-comparison-v8-v10.png`；左侧为 v8，右侧为 v10。
- 动效证据：`qa/method-river-rapids-final-motion-v10.png`；包含连续 A / B 帧和放大后的运动差异图。全画面平均绝对像素差为 1.326，变化集中在中央河道及局部岸边，群山和文字保持稳定。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 水势：在原有顺流纹理位移上增加中游横向破浪带、斜向碎浪、远近不同的流速与近景更强的法线扰动。急流不再由一条 S 形线往返，而是整条河内多尺度水纹共同向远处推进。
- 白浪：横向浪带用多层噪声打散，避免整齐重复的“斑马线”；暖白浪尖只出现在急流阈值较高的位置，近景更明显，远景更轻，不会把宣纸色调漂白。
- 拍岸：河岸被分为错开的水段，按随机种子交替在左右岸产生短暂冲击；拍岸只影响河岸窄带，不移动山体，也不形成整岸同步闪烁。
- 构图与文案：`method-river-rapids-final-comparison-v8-v10.png` 显示经典三句、右侧呼吸引导、山体明度、底部 CTA 的位置与 v8 一致；本轮没有修改第 1 页或提前加入第 3 页内容。
- 响应式：桌面和手机均无横向溢出、文字遮挡、画布硬边或河道掩膜外泄。手机仍采用纵向长卷构图，急流密度随河道透视收束。
- 交互与无障碍：经典三句仍为原生按钮，悬停/键盘焦点加粗放大，点击后保留两倍逐字书写；`prefers-reduced-motion: reduce` 下 WebGL 河流画布不显示，回退到完整静态山水图。
- 控制台：页面没有可复现的运行时错误；浏览器控制层出现一次外部 Statsig 遥测超时，与页面代码和水流渲染无关。

## 工程验证

- `vinext build`：通过。
- `node --test --test-name-pattern='method lines retain' tests/rendered-html.test.mjs`：1 / 1 通过；断言覆盖急流带、噪声打散、拍岸与白浪层存在。
- `node --test tests/preview-poll.test.mjs tests/rendered-html.test.mjs tests/result-presentation.test.mjs`：23 / 23 通过。
- ESLint：0 error；19 个项目既有 `<img>` 优化 warning。
- 未修改确定性排盘规则、AI/排盘边界或旧版入口；未部署、未提交、未推送。

final result: passed

---
