# 图像来源

- `fuxi-bagua-taiji.svg`：Wikimedia Commons `File:BatQuaiDo.svg`，作者 Connormah，CC BY-SA 3.0 / GFDL。原图未改动，仅在网页中通过 CSS 调整尺寸、透明度与颜色。
- 来源页：https://commons.wikimedia.org/wiki/File:BatQuaiDo.svg
- CC BY-SA 3.0：https://creativecommons.org/licenses/by-sa/3.0/

## 首页入境资产

- `hero-entry-v1.png`：依据用户选定的首页视觉，由 OpenAI 图像生成能力进行局部编辑；仅移除需要改为交互层的经典引文、横线、尾印与向下箭头，保留原定宋画构图。
- `hero-entry-mobile-v1.png`：从同一份已审定首页母版重排生成的移动端竖屏构图；保持原书法、题签和山水内容，避免横图强制裁切造成品牌残缺。
- `hero-ink-whispers-v2.png`：以用户最终确认的引文截图为唯一效果基准生成；仅保留四处彼此分离的轻墨云，并通过色键去除背景，作为题字后的透明交互层。
- `hero-down-cue-v1.png`：由 OpenAI 图像生成能力生成，并通过色键去除背景，作为首页最轻量的向下阅读提示。
- `hero-entry-wide-v3.png`、`hero-entry-square-v3.png`、`hero-entry-mobile-v3.png`：以用户审定的三套响应式首页构图为编辑目标，由 OpenAI 图像编辑能力移除烘焙在背景中的墨滴、永久水波、中央船、飞鸟群和瀑布，重建为用于分层动画的干净背景板；题字、引文、题签、山水、竹木、建筑与入口保持原构图。
- `hero-ink-drop-v2.png`：由 OpenAI 图像生成能力生成的单枚较大水墨液滴，经绿色色键处理为透明 PNG。
- `hero-ripple-ring-v1.png`：由 OpenAI 图像生成能力生成的单圈俯视水墨涟漪，经绿色色键处理为透明 PNG；网页以同一真实位图错时扩散形成连续水波，不使用代码绘制圆环。
- `hero-taiji-breath-v2.png`：由 OpenAI 图像生成能力生成的淡墨太极，经绿色色键处理为透明 PNG，用于题字背后的低透明度呼吸显隐。
- `hero-birds-v1.png`、`hero-boat-v1.png`、`hero-waterfall-v1.png`：由 OpenAI 图像生成能力生成并经绿色色键处理的独立透明环境素材，分别用于飞行、漂移和错相位下落动画。

## 第三页「正问」资产

- `question-pine-cloud-base-v2.webp`：以用户选定的孤松云海画面为基础，由 OpenAI 图像编辑能力移除松树，保留宣纸、远山、近石与原始云雾，作为满屏山水底板。
- `question-pine-tree-v2.png`：由同一审定画面提取的完整孤松透明层，以树根为固定轴进行轻微风摆。
- `question-cloud-stream-v3-tile.png`：参照已审定云海笔触，由 OpenAI 图像生成能力重构为横贯画面的流线型云河；经品红色键去底、暖灰化与左右边缘周期融合后成为无缝循环透明 PNG，始终从左向右流动。
- `question-mountain-occluder-v3.png`：从无松树底板确定性提取的前景山体透明遮挡层；置于远云前方，使云河在山峰处自然分流、穿谷和时隐时现。
- `question-cloud-veil-v4.png`、`question-cloud-fork-v4.png`、`question-cloud-bank-v4.png`：依据本页宋代水墨画面分别生成的斜向薄云、绕峰分流云与近景翻涌云，经品红色键去底、暖灰去色与透明边缘校正。三张云图沿不同曲线独立穿越画面，完整离场后才重置，不再首尾拼接或复用同一接缝。
- `question-cloudfall-base-v5.webp`：以用户选定的第二张云瀑概念图为视觉真值，由 OpenAI 图像编辑能力移除云雾和松树并补全山体，形成云海动效的静态山水底板。
- `question-cloudfall-mountain-v5.png`：从同一底板按墨色明度机械提取的透明山体前景层，用于让程序生成的云在主峰后汇聚、受山峰遮挡后分流，并在背风坡前方下泄。
- `question-cloudfall-base-v6.png`：最终采用的云海景深底板。基于用户选定的第二张概念图，仅移除左下前景松树与石基，完整保留迎风云海、主峰宽瀑、右侧窄瀑、远山与宣纸肌理；WebGL 动效只在其上生成不断变化的翻涌高光和游丝，因此没有平铺接缝。
- `question-cloudfall-final-v7.png`：用户于前七页线上验收时重新提供的第三页原始定稿画面，完整保留左下孤松、承托山石、坡脚杂树草木、迎风云海、双瀑与远山；作为本页最终静态视觉真值，动态云瀑仅在其上叠加。

## 声音

- `audio/guqin-zheng-diao.ogg`：Wikimedia Commons `File:Zheng diao.ogg`，Charlie Huang，古琴正调定弦录音，作者释放至公有领域。
- 来源页：https://commons.wikimedia.org/wiki/File:Zheng_diao.ogg

## 成卦牡丹背景

- `casting-peony-background-v3.webp`：以第一版牡丹枝条背景为编辑目标、以当前成卦页三朵花的实际叠加位置为校准，由 OpenAI 图像生成能力编辑。原位保留并增强三条承接花朵的枝干、花托与牡丹叶，移除竹子、树冠、山石、建筑、桥船与人物；底色调整为与前序长卷一致的冷灰米白宣纸。

## 定问落霞秋水背景

- `final-question-sunset-reeds-v1.webp`：以“落霞与孤鹜齐飞，秋水共长天一色”为主题，由 OpenAI 图像生成能力创作并经用户最终选定。近景为芦苇荡，远景保留秋水、远山、飞鸟与精细亭子；网页复用同一真实位图分出近景、中景芦苇与右上红霞的局部动效层，不使用代码绘制芦苇或云霞。
- `final-question-sunset-reeds-v2.png`：以上一版定问背景为编辑目标，由 OpenAI 图像生成能力仅移除原图中静止飞鸟，并重建对应的落霞天空，用于将红霞与飞鸟拆分成独立动画层；其余构图、色调、芦苇、秋水、远山与亭子保持一致。
- `final-question-bird-sprite-v1.png`：由 OpenAI 图像生成能力创作的四帧水墨白鹭振翅序列，经绿色色键处理为透明 PNG；网页逐帧切换真实位图形成振翅，并仅在原位置附近轻微浮动。
