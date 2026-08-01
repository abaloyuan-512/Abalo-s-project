# 第三页「正问」云瀑动效 QA（2026-08-01）

## 对照依据

- 用户选定的视觉真值：`C:\Users\27622\.codex\generated_images\019fa5e9-2a61-7f92-813b-b9d609ccb12c\exec-04c25898-61ae-4837-92eb-6bbe9106ac01.png`（第二张概念图）。
- 最终无松树景深底板：`public/question-cloudfall-base-v6.png`。
- 浏览器实拍两帧：`qa/inquiry-cloudfall-v6-browser-t1.png`、`qa/inquiry-cloudfall-v6-browser-t2.png`。
- 同画布对照：`qa/inquiry-cloudfall-v6-comparison.png`；两帧放大差异：`qa/inquiry-cloudfall-v6-motion-diff.png`。
- 验证环境：隔离的 Chrome，CSS viewport 1914 × 1018，devicePixelRatio 1，页面状态 `#inquiry`、问题为空。

## Findings

- 无剩余 P0 / P1 / P2 问题。
- 构图与选定概念一致：云海从左上迎风面汇入主峰，在峰顶分为一宽一窄两股，分别沿主峰左坡与右侧山谷下泄；远山、宣纸底色、墨色密度和左侧松树关系保持一致。
- 云海不使用平铺或首尾拼接图片。静态景深底板提供真实云体与软边，两个 WebGL 层只生成连续翻涌、内部明暗和游丝，因而不存在三角形接缝、图片边缘或整层往返平移。
- 前后景关系成立：迎风云团位于山体后方，宽窄云瀑在山体前方下泄；山体与正文之间加入无边界的宣纸雾化层，正文、例句和计数均保持可读，没有形成卡片边框。
- 松树仍为独立透明图层，保持用户已认可的轻微随风摇动；背景底板已移除静态松树，因此没有双影。
- 页面背景覆盖完整视口，右侧无空白边。

## 动效与交互验证

- 两帧相隔 8 秒，平均 RGB 差异为 1.606；阈值大于 2 的变化像素为 279,357，占整幅 14.34%。差异区域集中在迎风云团、两条云瀑、谷底游丝和松针，不是整张背景平移。
- 两个 canvas 均为 1914 × 1018，WebGL 正常创建；`IntersectionObserver` 在离屏时暂停，`prefers-reduced-motion` 下固定到静态时刻。
- 浏览器 Runtime exceptions：0；Log errors：0。
- 输入真实问题“我是否应该继续投入这次合作？”后，计数显示 14 / 160，“写好了，继续辨识”按钮从 disabled 变为可用。

## 工程验证

- Vinext production build：passed。
- Node rendered/interaction tests：28 / 28 passed。
- ESLint：0 errors；14 个既有 `<img>` / ARIA warnings，无新增 error。
- 未修改确定性排盘、规则版本、Python 引擎或第三页以外的业务流程；本轮未发布线上版本。

final result: passed
