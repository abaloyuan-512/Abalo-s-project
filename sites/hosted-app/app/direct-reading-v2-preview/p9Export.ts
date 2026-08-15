export type Page9ExportAct = {
  title: string;
  subtitle: string;
  body: readonly string[];
  art: "base" | "mutual" | "moving" | "changed" | "strength";
};

export type Page9ExportBundle = {
  numbers: readonly [number, number, number];
  cast: {
    base: string;
    mutual: string;
    moving: string;
    changed: string;
    canonical_line: string;
  };
  page8_acts: readonly Page9ExportAct[];
};

export type Page9ExportContent = {
  question: string;
  gua_label: string;
  answer: readonly [string, string];
  full_reading_markdown: string;
  export_bundle?: Page9ExportBundle;
};

export const READING_EXPORT_ASSET_PATHS = {
  font: "/fonts/ma-shan-zheng-sc.woff2",
  p3Cloud: "/question-pine-cloud-base-v2.webp",
  p3Tree: "/question-pine-tree-v2.png",
  p7: "/page7-taiji-bg-v1.png",
  p8Base: "/page8/page8-ben-gua-background-v6.png",
  p8Mutual: "/page8/page8-hu-gua-background-v6.png",
  p8Moving: "/page8/page8-dong-yao-background-v6.png",
  p8Changed: "/page8/page8-bian-gua-background-v6.png",
  p8Strength: "/page8/page8-wang-shuai-background-v6.png",
  p9: "/direct-reading-v2-preview/p9-celestial-background-v2.webp",
} as const;

export type ReadingExportAssetKey = keyof typeof READING_EXPORT_ASSET_PATHS;
export type ReadingExportAssets = Partial<Record<ReadingExportAssetKey, string>>;

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character] ?? character);
}

function paragraphs(lines: readonly string[]): string {
  return lines.map((line) => `<p>${escapeHtml(line)}</p>`).join("");
}

function page8AssetKey(art: Page9ExportAct["art"]): ReadingExportAssetKey {
  return {
    base: "p8Base",
    mutual: "p8Mutual",
    moving: "p8Moving",
    changed: "p8Changed",
    strength: "p8Strength",
  }[art] as ReadingExportAssetKey;
}

function dataAsset(assets: ReadingExportAssets, key: ReadingExportAssetKey): string {
  return escapeHtml(assets[key] ?? "");
}

export async function loadReadingExportAssets(): Promise<ReadingExportAssets> {
  const entries = await Promise.all(Object.entries(READING_EXPORT_ASSET_PATHS).map(async ([key, path]) => {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Unable to embed export asset: ${path}`);
    const blob = await response.blob();
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.addEventListener("load", () => resolve(String(reader.result)), { once: true });
      reader.addEventListener("error", () => reject(reader.error), { once: true });
      reader.readAsDataURL(blob);
    });
    return [key as ReadingExportAssetKey, dataUrl] as const;
  }));
  return Object.fromEntries(entries) as ReadingExportAssets;
}

export function buildReadingHtml(content: Page9ExportContent, assets: ReadingExportAssets): string {
  const bundle = content.export_bundle;
  const acts = bundle?.page8_acts ?? [{
    title: "完整解卦",
    subtitle: content.gua_label,
    body: [content.full_reading_markdown],
    art: "base" as const,
  }];
  const p8Pages = acts.map((act, index) => `
    <section class="sheet page8" style="--scene:url('${dataAsset(assets, page8AssetKey(act.art))}')">
      <div class="scene-copy ${index % 2 ? "right" : "left"}">
        <p class="eyebrow">第八页 · 第${["一", "二", "三", "四", "五"][index] ?? index + 1}幕</p>
        <h2>${escapeHtml(act.title)}</h2>
        <p class="subtitle">${escapeHtml(act.subtitle)}</p>
        <div class="reading-copy">${paragraphs(act.body)}</div>
      </div>
    </section>`).join("");
  const cast = bundle?.cast;
  const numbers = bundle?.numbers.join(" · ") ?? "—";

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>观象 · ${escapeHtml(content.gua_label)}</title>
  <style>
    @font-face{font-family:GuanxiangBrush;src:url('${dataAsset(assets, "font")}') format('woff2');font-display:swap}
    :root{--paper:#f2ead9;--ink:#2d2923;--soft:#6d675d;--cinnabar:#713c31;--rule:rgba(77,67,55,.2)}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:KaiTi,STKaiti,"Noto Serif SC",serif;letter-spacing:.045em}
    .sheet{position:relative;isolation:isolate;min-height:100svh;overflow:hidden;padding:clamp(36px,7vw,112px);display:grid;align-content:center;break-after:page;background-color:var(--paper);background-position:center;background-size:cover;background-repeat:no-repeat}
    .sheet::after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,rgba(246,239,224,.83),rgba(246,239,224,.2) 58%,rgba(246,239,224,.55));pointer-events:none}
    .eyebrow{margin:0 0 18px;color:var(--cinnabar);font-size:13px;letter-spacing:.22em}.seal{position:absolute;right:5vw;bottom:5vh;color:rgba(113,60,49,.68);font:400 18px/1 GuanxiangBrush,KaiTi,serif;writing-mode:vertical-rl}
    h1,h2{margin:0;font-family:GuanxiangBrush,KaiTi,serif;font-weight:400}h1{max-width:980px;font-size:clamp(34px,5vw,76px);line-height:1.42}h2{font-size:clamp(38px,5vw,68px);line-height:1.25}.subtitle{color:var(--soft);font-size:clamp(15px,1.35vw,20px);line-height:1.8}
    .p3{background-image:url('${dataAsset(assets, "p3Cloud")}')}.p3::before{content:"";position:absolute;z-index:-1;inset:0;background:url('${dataAsset(assets, "p3Tree")}') left bottom/auto 92% no-repeat;opacity:.88}.p3 .question{width:min(880px,68vw);margin-left:auto;padding-right:5vw}.p3 blockquote{margin:42px 0 0;padding:22px 0 22px 28px;border-left:2px solid rgba(113,60,49,.52);font-size:clamp(20px,2.2vw,31px);line-height:1.75}
    .p7{background-image:url('${dataAsset(assets, "p7")}');text-align:center}.p7::after{background:rgba(244,236,220,.28)}.cast-grid{width:min(980px,100%);margin:38px auto 0;display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.cast-grid article{padding:28px 14px;border-block:1px solid var(--rule);background:rgba(246,239,224,.42)}.cast-grid span{display:block;color:var(--cinnabar);font-size:12px;letter-spacing:.18em}.cast-grid b{display:block;margin-top:13px;font:400 clamp(24px,2.7vw,40px)/1.3 GuanxiangBrush,KaiTi,serif}.line-text{max-width:700px;margin:36px auto 0;color:var(--soft);line-height:1.9}.numbers{margin-top:20px;color:var(--cinnabar);font-size:13px;letter-spacing:.2em}
    .page8{background-image:var(--scene)}.scene-copy{width:min(660px,50vw);padding:38px clamp(24px,3.8vw,62px);background:rgba(244,237,223,.78);box-shadow:0 18px 70px rgba(64,51,38,.08)}.scene-copy.right{margin-left:auto}.reading-copy{margin-top:28px}.reading-copy p{margin:0 0 1em;color:#413d36;font-size:clamp(15px,1.15vw,18px);line-height:1.9}
    .p9{background-image:url('${dataAsset(assets, "p9")}');text-align:center}.p9::after{background:rgba(244,237,223,.23)}.p9 .finale{margin:auto}.p9 h2{letter-spacing:.12em}.p9 .gua{margin-top:12px;color:rgba(45,41,35,.6)}.answer{margin-top:clamp(58px,9vh,100px);font:400 clamp(27px,3vw,45px)/1.7 GuanxiangBrush,KaiTi,serif}.answer p{margin:0}.answer p+ p{color:var(--cinnabar)}.offline-note{margin-top:64px;color:rgba(45,41,35,.52);font-size:12px}
    @media(max-width:760px){.sheet{padding:32px 22px}.p3 .question,.scene-copy{width:100%;padding:26px 22px}.p3 blockquote{font-size:21px}.cast-grid{grid-template-columns:1fr 1fr}.scene-copy.right{margin-left:0}.reading-copy p{font-size:15px}.p9 .answer{font-size:26px}}
    @media print{.sheet{min-height:100vh}.offline-note{display:none}}
  </style>
</head>
<body>
  <main>
    <section class="sheet p3">
      <div class="question"><p class="eyebrow">第三页 · 所问之事</p><h1>${escapeHtml(content.question)}</h1><blockquote>一事一问，所问越明，所见越清。</blockquote></div><span class="seal">观象</span>
    </section>
    <section class="sheet p7">
      <div><p class="eyebrow">第七页 · 成卦</p><h2>${escapeHtml(content.gua_label)}</h2><p class="numbers">取数 ${escapeHtml(numbers)}</p>
        <div class="cast-grid"><article><span>本卦</span><b>${escapeHtml(cast?.base ?? content.gua_label)}</b></article><article><span>互卦</span><b>${escapeHtml(cast?.mutual ?? "—")}</b></article><article><span>动爻</span><b>${escapeHtml(cast?.moving ?? "—")}</b></article><article><span>变卦</span><b>${escapeHtml(cast?.changed ?? "—")}</b></article></div>
        <p class="line-text">${escapeHtml(cast?.canonical_line ?? "")}</p>
      </div>
    </section>
    ${p8Pages}
    <section class="sheet p9">
      <div class="finale"><p class="eyebrow">第九页</p><h2>观象寄语</h2><p class="gua">${escapeHtml(content.gua_label)}</p><div class="answer"><p>${escapeHtml(content.answer[0])}</p><p>${escapeHtml(content.answer[1])}</p></div><p class="offline-note">本文件已将 P3、P7、P8 五幕与 P9 美术资源嵌入，可离线打开。</p></div>
    </section>
  </main>
</body>
</html>`;
}

export function readingExportFilename(content: Page9ExportContent): string {
  const safeGua = content.gua_label.replace(/[\\/:*?"<>|\s·→]+/g, "-").replace(/^-|-$/g, "");
  return `观象-${safeGua || "本次解卦"}.html`;
}
