# 第八页五幕定稿资产

第八页顺序固定为：本卦、互卦、动爻、变卦、旺衰。

每幕只保留三张生产资产：

| 版面 | 定稿背景 | 云气层 | 鲲与点睛层 |
| --- | --- | --- | --- |
| 本卦 | `page8-ben-gua-background-v6.png` | `page8-ben-gua-mist-v1.png` | `page8-ben-gua-breath-v1.png` |
| 互卦 | `page8-hu-gua-background-v6.png` | `page8-hu-gua-mist-v1.png` | `page8-hu-gua-breath-v1.png` |
| 动爻 | `page8-dong-yao-background-v6.png` | `page8-dong-yao-mist-v1.png` | `page8-dong-yao-breath-v1.png` |
| 变卦 | `page8-bian-gua-background-v6.png` | `page8-bian-gua-mist-v1.png` | `page8-bian-gua-breath-v1.png` |
| 旺衰 | `page8-wang-shuai-background-v6.png` | `page8-wang-shuai-mist-v1.png` | `page8-wang-shuai-breath-v1.png` |

## 定稿约束

- `background-v6.png` 是最终暖米黄宣纸背景，不得回退引用 `v1` 至 `v5`。
- `mist-v1.png` 只用于极慢的云气推移、聚散与透明度呼吸。
- `breath-v1.png` 只用于鲲与点睛区域的亚像素位移和轻微浓淡变化。
- 五幕共享的银河光子河由 `GuanxiangApp.tsx` 中的 Canvas 动效实时绘制，不使用静态拖尾图片。
- 原始备份、中间调色稿、旧拖尾图和视觉实验页均已在定稿时移除，避免后续误引用。
