import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import SafeDirectReadingMarkdown, {
  parseSafeMarkdown,
} from "../app/direct-reading-v2-preview/SafeDirectReadingMarkdown";
import { shouldContinuePolling } from "../app/direct-reading-v2-preview/pollPolicy";
import ProductPresentationView, {
  Page9FinaleView,
  buildObservationRecord,
  buildReadingHtml,
  chooseP9StarBurst,
  readingExportFilename,
  type Page9FinaleContent,
  type ProductPresentation,
} from "../app/direct-reading-v2-preview/ProductPresentation";

test("safe renderer preserves useful Markdown structure", () => {
  const html = renderToStaticMarkup(
    <SafeDirectReadingMarkdown source={"## 判断\n\n可以开始探索。\n\n- 做现实核验\n- 保留缓冲\n\n> 不保证结果"} />,
  );
  assert.match(html, /<h2>判断<\/h2>/);
  assert.match(html, /<ul><li>做现实核验<\/li><li>保留缓冲<\/li><\/ul>/);
  assert.match(html, /<blockquote>不保证结果<\/blockquote>/);
});

test("active HTML and dangerous URL syntax render only as escaped text", () => {
  const attacks = [
    "<script>alert(1)</script>",
    "<IFRAME src=javascript:alert(1)></IFRAME>",
    "<svg onload=alert(1)>",
    "<math href=javascript:alert(1)>",
    "<img src=x onerror=alert(1)>",
    "<style>@import 'evil'</style>",
    "[点击](javascript:alert(1))",
    "[数据](data:text/html,<script>alert(1)</script>)",
    "[文件](file:///etc/passwd)",
    "[旧协议](vbscript:msgbox(1))",
    "&lt;script&gt;alert(1)&lt;/script&gt;",
  ];
  for (const attack of attacks) {
    const html = renderToStaticMarkup(<SafeDirectReadingMarkdown source={`## 判断\n\n${attack}`} />);
    assert.doesNotMatch(html, /<(?:script|iframe|svg|math|img|style)\b/i);
    assert.doesNotMatch(html, /<(?:a|iframe|svg|math|img|style)[^>]+(?:href|src|onload|onerror|style)=/i);
    assert.doesNotMatch(html, /dangerouslySetInnerHTML/);
    assert.match(html, /<p>/);
  }
});

test("parser does not create link or HTML node types", () => {
  const blocks = parseSafeMarkdown("## 判断\n\n<a href=javascript:alert(1)>点我</a>\n\n- [链接](data:text/html,x)");
  assert.deepEqual(new Set(blocks.map((block) => block.kind)), new Set(["heading", "paragraph", "list"]));
});

test("preview is isolated and never retries the POST", async () => {
  const page = await readFile(new URL("../app/direct-reading-v2-preview/page.tsx", import.meta.url), "utf8");
  const route = await readFile(new URL("../app/api/direct-reading/v2/route.ts", import.meta.url), "utf8");
  assert.equal((page.match(/method:\s*"POST"/g) ?? []).length, 1);
  assert.match(page, /setTimeout\(\(\) => void poll\(id\)/);
  assert.match(page, /sessionStorage\.setItem\(ACTIVE_REQUEST_KEY, id\)/);
  assert.match(page, /sessionStorage\.getItem\(ACTIVE_REQUEST_KEY\)/);
  assert.match(page, /POLL_LIMIT_ATTEMPTS = 140/);
  assert.match(page, /minLength=\{6\}/);
  assert.match(page, /payload\.chart_facts \?\? payload\.direct_reading\?\.chart_facts/);
  assert.match(page, /aria-label="确定性排盘"/);
  assert.match(page, /process\.env\.NODE_ENV !== "development"/);
  assert.match(page, /get\("offline-p9"\) !== "1"/);
  assert.match(page, /data-offline-p9-review="true"/);
  assert.match(page, /CAST_READY/);
  assert.equal((page.match(/shouldContinuePolling\(response\.status, payload\.terminal\)/g) ?? []).length, 2);
  assert.doesNotMatch(page, /dangerouslySetInnerHTML/);
  assert.match(route, /isAuthenticatedOwner/);
  assert.match(route, /ABALO_DIRECT_READING_V2_PREVIEW_ENABLED/);
  assert.match(route, /publicAllowList/);
  for (const forbidden of ["question_sha256", "prompt_sha256", "response_id", "usage", "latency_ms"]) {
    assert.doesNotMatch(route, new RegExp(`\\b${forbidden}\\b`));
  }
});

test("known terminal errors stop polling while ambiguous service failures remain recoverable", () => {
  assert.equal(shouldContinuePolling(503, true), false);
  assert.equal(shouldContinuePolling(503, false), true);
  assert.equal(shouldContinuePolling(503, undefined), true);
  assert.equal(shouldContinuePolling(403, true), false);
});

test("default product view keeps the frozen P8/P9 source mapping untouched", () => {
  const section = (heading: string) => ({ heading, markdown: `## ${heading}\n\n${heading}正文。`, start_offset: 0, end_offset: 8, sha256: `${heading}-sha` });
  const hexagram = (role: "BASE" | "MUTUAL" | "CHANGED", name: string, heading: string) => ({
    program_fact: { role, king_wen_number: 1, name, upper_trigram: "乾", lower_trigram: "坤" },
    model_section: section(heading),
  });
  const presentation = {
    contract_version: "SITES_DIRECT_HIGH_P8_P9_PRODUCT_V1",
    source_reading_sha256: "A".repeat(64),
    reconstructed_reading_sha256: "A".repeat(64),
    reconstructed_equals_source: true,
    page8: {
      responsibility: "BASE_MUTUAL_MOVING_CHANGED_PROGRAM_STRENGTH",
      base_hexagram: hexagram("BASE", "本卦名", "本卦：本卦名"),
      mutual_hexagram: hexagram("MUTUAL", "互卦名", "互卦：互卦名"),
      moving_line: { program_fact: { position: 3, name: "六三", canonical_line_text: "爻辞" }, model_section: section("动爻：六三") },
      changed_hexagram: hexagram("CHANGED", "变卦名", "变卦：变卦名"),
      program_strength: { source: "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH", body_trigram: "乾", initial_use_trigram: "坤", changed_use_trigram: "离", initial_relation: "体克用", changed_relation: "用生体", body_strength: "旺" },
    },
    page9: {
      responsibility: "JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS",
      judgment: section("判断"), suitable_actions: section("适合做什么"), unsuitable_actions: section("不适合做什么"), reverse_risk: section("反向风险"), change_signals: section("哪些现实信号会改变判断"),
    },
  } satisfies ProductPresentation;
  const html = renderToStaticMarkup(<ProductPresentationView presentation={presentation} />);
  assert.match(html, /P8 · 读卦五幕/);
  assert.match(html, /PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH/);
  assert.match(html, /P9 · 决策落地/);
  assert.equal((html.match(/>判断正文。</g) ?? []).length, 1);
  assert.equal((html.match(/>本卦：本卦名正文。</g) ?? []).length, 1);
});

test("P9 finale is one answer with continue and share actions, without a classic coda or five panels", () => {
  const content = {
    content_version: "GUANXIANG_P9_FINALE_OFFLINE_V1",
    record_id: "case-21-4-27",
    question: "是否开始共同搬家？",
    gua_label: "火雷噬嗑 · 九四 → 山雷颐",
    answer: ["可以开始，不必急着搬完。", "过得下去，比搬得过去要紧。"],
    full_reading_markdown: "## 判断\n\n完整正文。",
  } satisfies Page9FinaleContent;
  const html = renderToStaticMarkup(<Page9FinaleView content={content} />);

  assert.match(html, /id="p9-title">观象寄语/);
  assert.doesNotMatch(html, /P9 · 终章|此卦至此|page9Eyebrow/);
  assert.match(html, /可以开始，不必急着搬完。/);
  assert.match(html, /过得下去，比搬得过去要紧。/);
  assert.match(html, />继续追问</);
  assert.match(html, /href="\/?\?continue-question=1#inquiry"/);
  assert.match(html, />分享解卦</);
  assert.match(html, /本次观象已为您保存，可以前往观事簿进行回看。/);
  assert.doesNotMatch(html, /分享包含 P3、P7、P8 五幕与 P9/);
  assert.doesNotMatch(html, />存入观事簿<|>导出本次解卦</);
  assert.match(html, /p9-celestial-background-v2\.webp/);
  assert.equal((html.match(/<img[^>]+p9-star-spark-v1\.png/g) ?? []).length, 8);
  assert.match(html, /class="page9StarField" aria-hidden="true"/);
  assert.doesNotMatch(html, /role="tab"|role="tabpanel"/);
  assert.doesNotMatch(html, /一卦一语|知止不殆|适合做|不适合做|反向风险|转向条件/);
});

test("P9 star bursts always select one to three unique stars", () => {
  assert.deepEqual(chooseP9StarBurst(() => 0), [0]);

  const samples = [0.99, 0, 0.42, 0.99];
  let cursor = 0;
  const burst = chooseP9StarBurst(() => samples[cursor++] ?? 0);
  assert.equal(burst.length, 3);
  assert.equal(new Set(burst).size, burst.length);
  assert.ok(burst.every((index) => index >= 0 && index < 7));
});

test("P9 stars keep a quiet native-color shimmer between stronger bursts", async () => {
  const css = await readFile(new URL("../app/direct-reading-v2-preview/page.module.css", import.meta.url), "utf8");

  assert.match(css, /page9-star-breathe var\(--page9-star-duration/);
  assert.match(css, /page9-synthetic-star-breathe var\(--page9-star-duration/);
  assert.match(css, /grayscale\(\.82\)[\s\S]+brightness\(1\.34\)[\s\S]+drop-shadow/);
  assert.match(css, /mix-blend-mode: screen/);
  assert.match(css, /page9Star\[data-active="true"\][\s\S]+page9-star-burst 4\.2s/);
  assert.match(css, /scale\(3\.25\)/);
});

test("continue question is an explicit, query-gated return to the existing P3 textarea", async () => {
  const app = await readFile(new URL("../app/GuanxiangApp.tsx", import.meta.url), "utf8");
  assert.match(app, /searchParams\.get\("continue-question"\) !== "1"/);
  assert.match(app, /flowPageRef\.current = 3/);
  assert.match(app, /setMethodReady\(true\)/);
  assert.match(app, /setFlowPage\(3\)/);
  assert.match(app, /getElementById\("primary-question"\)\?\.focus/);
  assert.match(app, /<textarea id="primary-question"/);
});

test("P9 save and portable HTML export preserve the approved answer and complete reading", () => {
  const content = {
    content_version: "GUANXIANG_P9_FINALE_OFFLINE_V1",
    record_id: "case-21-4-27",
    question: "是否开始共同搬家？",
    gua_label: "火雷噬嗑 · 九四 → 山雷颐",
    answer: ["可以开始，不必急着搬完。", "过得下去，比搬得过去要紧。"],
    full_reading_markdown: "## 判断\n\n完整九章正文。",
    export_bundle: {
      numbers: [27, 44, 16],
      cast: { base: "火雷噬嗑", mutual: "水山蹇", moving: "九四", changed: "山雷颐", canonical_line: "噬乾胏，得金矢，利艰贞吉。" },
      page8_acts: [
        { title: "本卦", subtitle: "火雷噬嗑", body: ["本卦正文。"], art: "base" },
        { title: "互卦", subtitle: "水山蹇", body: ["互卦正文。"], art: "mutual" },
        { title: "动爻", subtitle: "九四", body: ["动爻正文。"], art: "moving" },
        { title: "变卦", subtitle: "山雷颐", body: ["变卦正文。"], art: "changed" },
        { title: "旺衰", subtitle: "程序事实", body: ["旺衰正文。"], art: "strength" },
      ],
    },
  } satisfies Page9FinaleContent;

  const record = buildObservationRecord(content, "2026-08-15T00:00:00.000Z");
  assert.equal(record.saved_at, "2026-08-15T00:00:00.000Z");
  assert.equal(record.full_reading_markdown, content.full_reading_markdown);

  const embedded = "data:image/png;base64,AAAA";
  const exported = buildReadingHtml(content, {
    font: "data:font/woff2;base64,AAAA", p3Cloud: embedded, p3Tree: embedded, p7: embedded,
    p8Base: embedded, p8Mutual: embedded, p8Moving: embedded, p8Changed: embedded, p8Strength: embedded, p9: embedded,
  });
  assert.match(exported, /第三页 · 所问之事/);
  assert.match(exported, /第七页 · 成卦/);
  assert.equal((exported.match(/第八页 · 第/g) ?? []).length, 5);
  assert.match(exported, /第九页/);
  assert.match(exported, /可以开始，不必急着搬完。/);
  assert.match(exported, /过得下去，比搬得过去要紧。/);
  assert.match(exported, /data:image\/png;base64,AAAA/);
  assert.doesNotMatch(exported, /src="https?:|url\(['"]?https?:/);
  assert.equal(readingExportFilename(content), "观象-火雷噬嗑-九四-山雷颐.html");
});

test("preview posts an explicit direct-high entry mode and requires product mapping", async () => {
  const page = await readFile(new URL("../app/direct-reading-v2-preview/page.tsx", import.meta.url), "utf8");
  assert.match(page, /type EntryMode = "CLEAR" \| "CONFIRMED" \| "SKIP"/);
  assert.match(page, /entry_mode: entryMode/);
  assert.match(page, /payload\.product_presentation/);
  assert.match(page, /payload\.direct_high\?\.route === "DIRECT_HIGH"/);
  assert.doesNotMatch(page, /router_outcome|ASK_ONCE|critical_ambiguity/);
});
