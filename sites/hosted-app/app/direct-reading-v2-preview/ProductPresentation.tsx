"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import SafeDirectReadingMarkdown from "./SafeDirectReadingMarkdown";
import { MobileScrollPetal } from "../MobileScrollPetal";
import {
  buildReadingHtml,
  loadReadingExportAssets,
  readingExportFilename,
  type Page9ExportBundle,
} from "./p9Export";

export { buildReadingHtml, readingExportFilename } from "./p9Export";

type SourceSection = {
  heading: string;
  markdown: string;
  start_offset: number;
  end_offset: number;
  sha256: string;
};

type HexagramScene = {
  program_fact: {
    role: "BASE" | "MUTUAL" | "CHANGED";
    king_wen_number: number;
    name: string;
    upper_trigram: string;
    lower_trigram: string;
  };
  model_section: SourceSection;
};

type MovingScene = {
  program_fact: {
    position: number;
    name: string;
    canonical_line_text: string;
  };
  model_section: SourceSection;
};

export type ProductPresentation = {
  contract_version: "SITES_DIRECT_HIGH_P8_P9_PRODUCT_V1";
  source_reading_sha256: string;
  reconstructed_reading_sha256: string;
  reconstructed_equals_source: true;
  prepared_chart_sha256: string;
  page8: {
    responsibility: "BASE_MUTUAL_MOVING_CHANGED_PROGRAM_STRENGTH";
    base_hexagram: HexagramScene;
    mutual_hexagram: HexagramScene;
    moving_line: MovingScene;
    changed_hexagram: HexagramScene;
    program_strength: {
      source: "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH";
      body_trigram: string;
      initial_use_trigram: string;
      changed_use_trigram: string;
      initial_relation: string;
      changed_relation: string;
      body_strength: string;
    };
  };
  page9: {
    responsibility: "JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS";
    judgment: SourceSection;
    suitable_actions: SourceSection;
    unsuitable_actions: SourceSection;
    reverse_risk: SourceSection;
    change_signals: SourceSection;
  };
};

export type Page9FinaleContent = {
  content_version: "GUANXIANG_P9_FINALE_V1";
  record_id: string;
  question: string;
  gua_label: string;
  answer: readonly [string, string];
  full_reading_markdown: string;
  export_bundle?: Page9ExportBundle;
};

function exportSectionBody(markdown: string): string[] {
  return markdown.replace(/^##[^\n]*\n+/, "").trim().split(/\n\s*\n/).filter(Boolean);
}

export function buildPage9FinaleContent(
  recordId: string,
  question: string,
  numbers: readonly number[],
  reading: string,
  presentation: ProductPresentation,
  answer: readonly [string, string],
): Page9FinaleContent {
  const { page8 } = presentation;
  return {
    content_version: "GUANXIANG_P9_FINALE_V1",
    record_id: recordId,
    question,
    gua_label: `${page8.base_hexagram.program_fact.name} · ${page8.moving_line.program_fact.name} → ${page8.changed_hexagram.program_fact.name}`,
    answer,
    full_reading_markdown: reading,
    export_bundle: {
      numbers: numbers as [number, number, number],
      cast: {
        base: page8.base_hexagram.program_fact.name,
        mutual: page8.mutual_hexagram.program_fact.name,
        moving: page8.moving_line.program_fact.name,
        changed: page8.changed_hexagram.program_fact.name,
        canonical_line: page8.moving_line.program_fact.canonical_line_text,
      },
      page8_acts: [
        { title: "本卦", subtitle: page8.base_hexagram.program_fact.name, art: "base", body: exportSectionBody(page8.base_hexagram.model_section.markdown) },
        { title: "互卦", subtitle: page8.mutual_hexagram.program_fact.name, art: "mutual", body: exportSectionBody(page8.mutual_hexagram.model_section.markdown) },
        { title: "动爻", subtitle: page8.moving_line.program_fact.name, art: "moving", body: exportSectionBody(page8.moving_line.model_section.markdown) },
        { title: "变卦", subtitle: page8.changed_hexagram.program_fact.name, art: "changed", body: exportSectionBody(page8.changed_hexagram.model_section.markdown) },
        {
          title: "旺衰",
          subtitle: `体卦 ${page8.program_strength.body_trigram}`,
          art: "strength",
          body: [
            `初始用卦 ${page8.program_strength.initial_use_trigram}，${page8.program_strength.initial_relation}。`,
            `变化用卦 ${page8.program_strength.changed_use_trigram}，${page8.program_strength.changed_relation}。`,
            `体卦旺衰：${page8.program_strength.body_strength}。`,
          ],
        },
      ],
    },
  };
}

type ObservationRecord = {
  record_id: string;
  question: string;
  gua_label: string;
  answer: readonly [string, string];
  full_reading_markdown: string;
  saved_at: string;
};

const OBSERVATION_BOOK_KEY = "guanxiang.observation-book.v1";
const P9_STAR_BURST_MS = 4200;

const P9_STARS: readonly { left: number; top: number; tianShu?: boolean; synthetic?: boolean; ambient?: boolean }[] = [
  { left: 17.9642, top: 9.4697, tianShu: true },
  { left: 20.582, top: 19.9023 },
  { left: 27.9199, top: 23.5849 },
  { left: 29.7428, top: 15.5029 },
  { left: 38.954, top: 16.1758 },
  { left: 44.3685, top: 13.8945, synthetic: true },
  { left: 49.832, top: 11.627 },
  { left: 60.8, top: 8.9, ambient: true },
  { left: 70.4, top: 13.7, ambient: true },
  { left: 81.6, top: 8.1, ambient: true },
  { left: 90.1, top: 17.2, ambient: true },
  { left: 58.2, top: 24.8, ambient: true },
  { left: 75.3, top: 27.1, ambient: true },
  { left: 88.4, top: 29.6, ambient: true },
  { left: 10.2, top: 14.6, ambient: true },
  { left: 8.1, top: 27.9, ambient: true },
  { left: 65.9, top: 34.1, ambient: true },
  { left: 93.2, top: 36.3, ambient: true },
  { left: 54.1, top: 5.6, ambient: true },
  { left: 66.3, top: 20.6, ambient: true },
  { left: 78.7, top: 20.9, ambient: true },
  { left: 96.1, top: 7.8, ambient: true },
  { left: 3.8, top: 8.7, ambient: true },
  { left: 5.2, top: 20.4, ambient: true },
  { left: 13.4, top: 34.2, ambient: true },
  { left: 23.7, top: 31.1, ambient: true },
  { left: 34.6, top: 28.7, ambient: true },
  { left: 48.1, top: 31.8, ambient: true },
  { left: 61.4, top: 39.4, ambient: true },
  { left: 72.1, top: 37.1, ambient: true },
  { left: 83.8, top: 39.7, ambient: true },
  { left: 96.6, top: 27.4, ambient: true },
  { left: 31.8, top: 6.2, ambient: true },
  { left: 41.7, top: 7.4, ambient: true },
  { left: 55.2, top: 17.4, ambient: true },
  { left: 16.8, top: 4.7, ambient: true },
  { left: 24.8, top: 8.3, ambient: true },
  { left: 52.7, top: 26.3, ambient: true },
  { left: 63.7, top: 31.4, ambient: true },
  { left: 73.7, top: 31.5, ambient: true },
  { left: 85.9, top: 33.5, ambient: true },
  { left: 3.4, top: 38.2, ambient: true },
  { left: 17.6, top: 41.6, ambient: true },
  { left: 30.2, top: 39.2, ambient: true },
  { left: 42.5, top: 41.7, ambient: true },
  { left: 54.7, top: 46.1, ambient: true },
  { left: 68.3, top: 44.8, ambient: true },
  { left: 79.4, top: 46.7, ambient: true },
  { left: 91.5, top: 43.9, ambient: true },
  { left: 6.7, top: 48.8, ambient: true },
  { left: 23.9, top: 47.2, ambient: true },
  { left: 37.1, top: 45.5, ambient: true },
  { left: 47.1, top: 11.5, ambient: true },
  { left: 91.2, top: 12.2, ambient: true },
  { left: 56.8, top: 12.1, ambient: true },
];

export function chooseP9StarBurst(random: () => number = Math.random): number[] {
  const count = Math.min(3, Math.max(1, Math.floor(random() * 3) + 1));
  const remaining = P9_STARS.map((_, index) => index);
  const selected: number[] = [];

  while (selected.length < count && remaining.length > 0) {
    const pick = Math.min(remaining.length - 1, Math.floor(random() * remaining.length));
    selected.push(remaining.splice(pick, 1)[0]);
  }

  return selected;
}

function P9StarField() {
  const [activeStars, setActiveStars] = useState<readonly number[]>([]);

  useEffect(() => {
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const pageVisible = () => document.visibilityState === "visible";
    let burstTimer: ReturnType<typeof setTimeout> | undefined;
    let clearTimer: ReturnType<typeof setTimeout> | undefined;

    const clearTimers = () => {
      if (burstTimer) window.clearTimeout(burstTimer);
      if (clearTimer) window.clearTimeout(clearTimer);
    };

    const scheduleBurst = () => {
      const pause = 700 + Math.random() * 1100;
      burstTimer = window.setTimeout(() => {
        if (!pageVisible()) {
          scheduleBurst();
          return;
        }
        setActiveStars(chooseP9StarBurst());
        clearTimer = window.setTimeout(() => {
          setActiveStars([]);
          scheduleBurst();
        }, P9_STAR_BURST_MS);
      }, pause);
    };

    const syncMotionPreference = () => {
      clearTimers();
      setActiveStars([]);
      if (!motionPreference.matches && pageVisible()) scheduleBurst();
    };

    syncMotionPreference();
    motionPreference.addEventListener("change", syncMotionPreference);
    document.addEventListener("visibilitychange", syncMotionPreference);

    return () => {
      clearTimers();
      motionPreference.removeEventListener("change", syncMotionPreference);
      document.removeEventListener("visibilitychange", syncMotionPreference);
    };
  }, []);

  const activeSet = new Set(activeStars);

  return (
    <div className="page9StarField" aria-hidden="true" data-active-count={activeStars.length} data-total-count={P9_STARS.length}>
      {P9_STARS.filter((star) => star.synthetic).map((star) => (
        <img
          key={`base-${star.left}-${star.top}`}
          className="page9BaseSyntheticStar"
          src="/direct-reading-v2-preview/p9-star-spark-v1.png"
          alt=""
          draggable="false"
          style={{
            left: `${star.left}%`,
            top: `${star.top}%`,
            "--page9-star-delay": "-1.9s",
            "--page9-star-duration": "3.8s",
          } as CSSProperties}
        />
      ))}
      {P9_STARS.map((star, index) => (
        <img
          key={`${star.left}-${star.top}`}
          className={`page9Star${star.tianShu ? " page9TianShu" : ""}${star.synthetic ? " page9SyntheticStar" : ""}${star.ambient ? " page9AmbientStar" : ""}`}
          src="/direct-reading-v2-preview/p9-star-spark-v1.png"
          alt=""
          draggable="false"
          data-active={activeSet.has(index) ? "true" : undefined}
          style={{
            left: `${star.left}%`,
            top: `${star.top}%`,
            "--page9-star-delay": `${-(index * .73 + .35).toFixed(2)}s`,
            "--page9-star-duration": `${(3.2 + (index % 3) * .55).toFixed(2)}s`,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}

export function buildObservationRecord(content: Page9FinaleContent, savedAt: string): ObservationRecord {
  return {
    record_id: content.record_id,
    question: content.question,
    gua_label: content.gua_label,
    answer: content.answer,
    full_reading_markdown: content.full_reading_markdown,
    saved_at: savedAt,
  };
}

function readObservationBook(): ObservationRecord[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(OBSERVATION_BOOK_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((item): item is ObservationRecord => (
      typeof item === "object" && item !== null && typeof (item as ObservationRecord).record_id === "string"
    )) : [];
  } catch {
    return [];
  }
}

function HexagramCard({ label, scene }: { label: string; scene: HexagramScene }) {
  return (
    <article className="productScene">
      <header>
        <span>{label} · 程序盘面</span>
        <strong>{scene.program_fact.name}</strong>
        <small>第 {scene.program_fact.king_wen_number} 卦 · 上{scene.program_fact.upper_trigram}下{scene.program_fact.lower_trigram}</small>
      </header>
      <SafeDirectReadingMarkdown source={scene.model_section.markdown} />
    </article>
  );
}

export function Page9FinaleView({ content }: { content: Page9FinaleContent }) {
  const [notice, setNotice] = useState("");
  const [bookOpen, setBookOpen] = useState(false);
  const [records, setRecords] = useState<ObservationRecord[]>([]);
  const [sharing, setSharing] = useState(false);
  const bookRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    try {
      const storedRecords = readObservationBook();
      const next = buildObservationRecord(content, new Date().toISOString());
      const existingIndex = storedRecords.findIndex((item) => item.record_id === content.record_id);
      if (existingIndex >= 0) storedRecords[existingIndex] = next;
      else storedRecords.unshift(next);
      window.localStorage.setItem(OBSERVATION_BOOK_KEY, JSON.stringify(storedRecords));
      queueMicrotask(() => setRecords([...storedRecords]));
    } catch {
      queueMicrotask(() => setNotice("本次未能自动保存，请检查浏览器是否允许本地记录。"));
    }
  }, [content.record_id]);

  useEffect(() => {
    if (!bookOpen) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const closeButton = bookRef.current?.querySelector<HTMLButtonElement>("button");
    closeButton?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setBookOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      previousFocus?.focus();
    };
  }, [bookOpen]);

  async function shareReading() {
    setSharing(true);
    try {
      const assets = await loadReadingExportAssets();
      const filename = readingExportFilename(content);
      const file = new File(["\uFEFF", buildReadingHtml(content, assets)], filename, { type: "text/html;charset=utf-8" });
      const sharePayload = { title: `观象 · ${content.gua_label}`, text: content.answer.join("\n"), files: [file] };
      if (navigator.share && (!navigator.canShare || navigator.canShare(sharePayload))) {
        try {
          await navigator.share(sharePayload);
          setNotice("已打开系统分享，可将本次完整解卦发送给他人。");
          return;
        } catch (caught) {
          if (caught instanceof DOMException && caught.name === "AbortError") {
            setNotice("已取消分享。");
            return;
          }
        }
      }
      const url = URL.createObjectURL(file);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setNotice("当前设备未提供系统分享，已生成可转发的完整 HTML。");
    } catch {
      setNotice("这次未能分享，请稍后再试。");
    } finally {
      setSharing(false);
    }
  }

  return (
    <section className="page9Finale" aria-labelledby="p9-title">
      <div className="page9ArtPlane" aria-hidden="true">
        <img
          className="page9Backdrop"
          src="/direct-reading-v2-preview/p9-celestial-background-v2.webp"
          alt=""
          draggable="false"
        />
        <P9StarField />
      </div>

      <header className="page9FinaleHeading">
        <h2 id="p9-title">观象寄语</h2>
        <p>{content.gua_label}</p>
      </header>

      <div className="page9Answer" aria-label="本次答案">
        <p>{content.answer[0]}</p>
        <p>{content.answer[1]}</p>
      </div>

      <div className="page9FinaleActions" aria-label="继续追问或分享本次解卦">
        {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
        <a className="page9Continue" href="/?continue-question=1#inquiry">继续追问</a>
        <button type="button" className="page9Share" onClick={() => void shareReading()} disabled={sharing}>{sharing ? "正在汇成画卷" : "分享解卦"}</button>
        <small><button type="button" className="page9BookLink" onClick={() => setBookOpen(true)}>本次观象已保存在当前浏览器，轻触打开观事簿回看。</button></small>
      </div>

      <p className="page9Notice" role="status" aria-live="polite">{notice}</p>

      {bookOpen ? <div className="page9BookBackdrop" onMouseDown={(event) => {
        if (event.target === event.currentTarget) setBookOpen(false);
      }}>
        <div className="page9BookFrame">
          <section ref={bookRef} className="page9Book" role="dialog" aria-modal="true" aria-labelledby="page9-book-title">
            <header><div><p>留待事后来证</p><h3 id="page9-book-title">观事簿</h3></div><button type="button" onClick={() => setBookOpen(false)} aria-label="关闭观事簿">收起</button></header>
            <p className="page9BookPrivacy">记录只保存在当前浏览器。这里可以重新打开本次问题、卦象与最后寄语。</p>
            <div className="page9BookList">
              {records.map((record, index) => <details key={`${record.record_id}-${record.saved_at}`} open={index === 0}>
                <summary><span>{new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(new Date(record.saved_at))}</span><strong>{record.gua_label}</strong></summary>
                <div><p className="page9BookQuestion">{record.question}</p><blockquote><p>{record.answer[0]}</p><p>{record.answer[1]}</p></blockquote></div>
              </details>)}
            </div>
          </section>
          <MobileScrollPetal containerRef={bookRef} />
        </div>
      </div> : null}
    </section>
  );
}

export default function ProductPresentationView({ presentation }: { presentation: ProductPresentation }) {
  const { page8 } = presentation;
  return (
    <section className="productPage" aria-labelledby="p8-title">
        <p className="eyebrow">P8 · 读卦五幕</p>
        <h2 id="p8-title">卦盘结构与四层解读</h2>
        <p className="productBoundary">四层解读逐字来自本次九章正文；第五幕只呈现同一次程序排盘的体用与旺衰，不承载建议或现实判断。</p>
        <div className="productScenes">
          <HexagramCard label="本卦" scene={page8.base_hexagram} />
          <HexagramCard label="互卦" scene={page8.mutual_hexagram} />
          <article className="productScene">
            <header>
              <span>动爻 · 程序盘面</span>
              <strong>{page8.moving_line.program_fact.name}</strong>
              <small>第 {page8.moving_line.program_fact.position} 爻 · {page8.moving_line.program_fact.canonical_line_text}</small>
            </header>
            <SafeDirectReadingMarkdown source={page8.moving_line.model_section.markdown} />
          </article>
          <HexagramCard label="变卦" scene={page8.changed_hexagram} />
          <article className="productScene programOnly">
            <header>
              <span>旺衰 · 仅程序事实</span>
              <strong>体卦 {page8.program_strength.body_trigram}</strong>
              <small>{page8.program_strength.source}</small>
            </header>
            <dl className="strengthGrid">
              <div><dt>初始用卦</dt><dd>{page8.program_strength.initial_use_trigram}</dd></div>
              <div><dt>变化用卦</dt><dd>{page8.program_strength.changed_use_trigram}</dd></div>
              <div><dt>初始体用</dt><dd>{page8.program_strength.initial_relation}</dd></div>
              <div><dt>变化体用</dt><dd>{page8.program_strength.changed_relation}</dd></div>
              <div><dt>体卦旺衰</dt><dd>{page8.program_strength.body_strength}</dd></div>
            </dl>
          </article>
        </div>
    </section>
  );
}
