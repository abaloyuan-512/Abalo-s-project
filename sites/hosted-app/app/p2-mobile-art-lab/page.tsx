"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import type { CSSProperties } from "react";
import RiverFlowCanvas from "./RiverFlowCanvas";
import styles from "./page.module.css";

type ConceptId = "river-spine" | "breath-paper" | "hanging-scroll";

type Concept = {
  id: ConceptId;
  name: string;
  thesis: string;
  composition: string;
  motion: string;
  risk: string;
};

const concepts: Concept[] = [
  {
    id: "river-spine",
    name: "江势为序",
    thesis: "把白浪当成阅读脊柱，让书法、呼吸与入口沿同一股江势自然下行。",
    composition: "题字居上游，解释落在中游静水，唯一入口压在下游；不是三块内容叠放。",
    motion: "水势只在手工勾勒的河道内分叉、汇流和翻卷，远山与岸线保持静止；悬停强调整句，点按呈现逐字落墨。",
    risk: "新水势由低功耗 WebGL 驱动，仍需在华为 Pura 70 Ultra 真机确认 GPU 表现与耗电。",
  },
  {
    id: "breath-paper",
    name: "三息留白",
    thesis: "把停顿本身做成画面，让三次呼吸发生在纸面的空处，而不是加一个呼吸组件。",
    composition: "山河退到上半幅，书法横跨云口；说明与入口分居下方两侧，中间留出真正的静默。",
    motion: "三道极淡水气依次舒展、回落，总周期 7.2 秒；书法点按是墨色由枯到润，不做模糊显现。",
    risk: "留白比例最大，需要真机确认鸿蒙浏览器底栏不会压缩呼吸区。",
  },
  {
    id: "hanging-scroll",
    name: "偏轴立卷",
    thesis: "把山河收成一轴会流动的立卷，让书法越过卷边，形成手机专属的纵向张力。",
    composition: "右侧窄卷承载山河，左侧纸面承载解释；三句题字跨越两者，入口落在卷尾。",
    motion: "卷内白浪缓慢上提 8px 后归位，像气息穿过长卷；点按以一笔朱砂旁注回应，不遮字。",
    risk: "偏轴最强，较依赖 430px 左右宽度；窄于 360px 时需单独压缩题字跨度。",
  },
];

const classicLines = ["在天成象", "在地成形", "变化见矣"];

function subscribeToLocation(callback: () => void) {
  window.addEventListener("popstate", callback);
  return () => window.removeEventListener("popstate", callback);
}

function useQueryState() {
  const search = useSyncExternalStore(subscribeToLocation, () => window.location.search, () => "");
  const query = new URLSearchParams(search);
  const requested = query.get("concept") as ConceptId | null;
  const queryConcept = requested && concepts.some((concept) => concept.id === requested) ? requested : "river-spine";
  const [conceptOverride, setConceptOverride] = useState<ConceptId | null>(null);
  const [sampleOverride, setSampleOverride] = useState<boolean | null>(null);
  const [motionOverride, setMotionOverride] = useState<boolean | null>(null);

  return {
    conceptId: conceptOverride ?? queryConcept,
    setConceptId: setConceptOverride,
    sampleOnly: sampleOverride ?? query.get("view") === "sample",
    setSampleOnly: setSampleOverride,
    motionOn: motionOverride ?? query.get("motion") !== "static",
    setMotionOn: setMotionOverride,
  };
}

export default function P2MobileArtLabPage() {
  const { conceptId, setConceptId, sampleOnly, setSampleOnly, motionOn, setMotionOn } = useQueryState();
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const [previewLine, setPreviewLine] = useState<number | null>(null);
  const [writingRun, setWritingRun] = useState(0);
  const [bridgeVisible, setBridgeVisible] = useState(false);
  const [bridgeElapsedMs, setBridgeElapsedMs] = useState<number | null>(null);
  const [ready, setReady] = useState(false);
  const bridgeTimer = useRef<number | null>(null);
  const bridgeStartedAt = useRef<number | null>(null);
  const writingTimer = useRef<number | null>(null);
  const concept = useMemo(() => concepts.find((item) => item.id === conceptId) ?? concepts[0], [conceptId]);
  const emphasizedLine = activeLine ?? previewLine;

  useEffect(() => () => {
    if (bridgeTimer.current !== null) window.clearTimeout(bridgeTimer.current);
    if (writingTimer.current !== null) window.clearTimeout(writingTimer.current);
  }, []);

  function chooseConcept(next: ConceptId) {
    if (bridgeTimer.current !== null) {
      window.clearTimeout(bridgeTimer.current);
      bridgeTimer.current = null;
    }
    setConceptId(next);
    setActiveLine(null);
    setPreviewLine(null);
    setReady(false);
    setBridgeVisible(false);
    setBridgeElapsedMs(null);
    const url = new URL(window.location.href);
    url.searchParams.set("concept", next);
    url.searchParams.delete("view");
    window.history.replaceState({}, "", url);
  }

  function activateLine(index: number) {
    if (writingTimer.current !== null) window.clearTimeout(writingTimer.current);
    setActiveLine(index);
    setPreviewLine(null);
    setWritingRun((run) => run + 1);
    writingTimer.current = window.setTimeout(() => {
      setActiveLine(null);
      writingTimer.current = null;
    }, 3_200);
  }

  function previewTransition() {
    if (ready) return;
    setReady(true);
    bridgeStartedAt.current = performance.now();
    bridgeTimer.current = window.setTimeout(() => {
      setBridgeElapsedMs(Math.round(performance.now() - (bridgeStartedAt.current ?? performance.now())));
      setBridgeVisible(true);
      bridgeTimer.current = null;
    }, 780);
  }

  return (
    <main className={`${styles.lab}${sampleOnly ? ` ${styles.sampleOnly}` : ""}`} data-concept={conceptId}>
      {!sampleOnly && (
        <header className={styles.reviewHeader}>
          <div>
            <p>移动端视觉优化 · P2</p>
            <h1>观象之法：A 方向返修</h1>
            <span>华为 Pura 70 Ultra 尺寸近似仿真，待产品负责人真机验收</span>
          </div>
          <div className={styles.reviewActions}>
            <button type="button" aria-pressed={!motionOn} onClick={() => setMotionOn(false)}>静态定帧</button>
            <button type="button" aria-pressed={motionOn} onClick={() => setMotionOn(true)}>动效样片</button>
            <button type="button" onClick={() => setSampleOnly(true)}>专注查看</button>
          </div>
        </header>
      )}

      {!sampleOnly && (
        <nav className={styles.conceptNav} aria-label="P2 候选方案">
          {concepts.map((item) => (
            <button key={item.id} type="button" aria-pressed={item.id === conceptId} onClick={() => chooseConcept(item.id)}>
              <b>{item.name}</b>
              <span>{item.thesis}</span>
            </button>
          ))}
        </nav>
      )}

      <section className={styles.reviewBody}>
        <div className={styles.phoneColumn}>
          <article className={`${styles.phone}${motionOn ? ` ${styles.motionOn}` : ` ${styles.motionOff}`}`} aria-label={`${concept.name}手机端样片`}>
            <div className={styles.scene}>
              <div className={styles.landscape} aria-hidden="true" />
              {conceptId === "river-spine" && <RiverFlowCanvas active={motionOn} />}
              <div className={styles.paperVeil} aria-hidden="true" />
              <div className={styles.breathCurrent} aria-hidden="true"><i /><i /><i /></div>
            </div>

            <div className={styles.brand} aria-label="观象"><b>观</b><b>象</b><i aria-hidden="true">观</i></div>

            <section className={styles.artStage} aria-labelledby="p2-lab-title">
              <div className={styles.quote}>
                <h2 id="p2-lab-title" aria-label="在天成象 在地成形 变化见矣" className={emphasizedLine === null ? undefined : styles.hasActiveLine}>
                  {classicLines.map((line, index) => (
                    <button
                      key={`${line}-${writingRun}`}
                      type="button"
                      className={(emphasizedLine === index ? styles.emphasizedLine : "") + (activeLine === index ? " " + styles.activeLine : "")}
                      aria-pressed={activeLine === index}
                      aria-label={`${line} 点击观看整句书写过程`}
                      onPointerEnter={(event) => {
                        if (event.pointerType !== "touch" && activeLine === null) setPreviewLine(index);
                      }}
                      onPointerLeave={(event) => {
                        if (event.pointerType !== "touch") setPreviewLine(null);
                      }}
                      onFocus={() => {
                        if (activeLine === null) setPreviewLine(index);
                      }}
                      onBlur={() => setPreviewLine(null)}
                      onClick={() => activateLine(index)}
                    >
                      <span className={styles.lineLabel}>{line}</span>
                      {activeLine === index && (
                        <span key={`${line}-${writingRun}`} className={styles.writingLayer} aria-hidden="true">
                          {Array.from(line).map((character, characterIndex) => (
                            <i key={`${character}-${characterIndex}`} style={{ "--char-index": characterIndex } as CSSProperties}>{character}</i>
                          ))}
                        </span>
                      )}
                    </button>
                  ))}
                </h2>
                <cite>《周易·系辞上》</cite>
              </div>

              <div className={styles.explainer}>
                <p className={styles.lead}>炁是流动的<br />也带动象的变化</p>
                <p className={styles.breathCopy}>
                  {conceptId === "river-spine" ? (
                    <span>请先放下急于知道答案的心<br />让我带你进入观象<br />现在缓缓做三次深呼吸<br />然后我们进入正问</span>
                  ) : (
                    <>
                      <span>请先放下急于知道答案的心<br />让我带你进入观象<br />现在缓缓做三次深呼吸<br />然后</span>
                      <b>进入第一步：正问</b>
                    </>
                  )}
                </p>
              </div>
            </section>

            <div className={styles.readiness}>
              <button type="button" aria-label="进入正问" aria-pressed={ready} onClick={previewTransition}>
                <span>{ready ? "正在入境" : "进入正问"}</span><i aria-hidden="true" />
              </button>
              <p role="status" aria-live="polite">{ready ? "准备状态已确认，正在进入正问。" : ""}</p>
            </div>

            {bridgeVisible && (
              <section className={styles.bridge} aria-label="P3 正问衔接样片" data-observed-delay-ms={bridgeElapsedMs ?? undefined}>
                <p>观象之法 · 壹</p>
                <h2>正问</h2>
                <span>此刻，你想问的是什么？</span>
                <button type="button" onClick={() => { setBridgeVisible(false); setReady(false); setBridgeElapsedMs(null); }}>返回 P2 样片</button>
              </section>
            )}
          </article>

        </div>

        {!sampleOnly && (
          <aside className={styles.notes}>
            <p>当前候选</p>
            <h2>{concept.name}</h2>
            <dl>
              <div><dt>构图逻辑</dt><dd>{concept.composition}</dd></div>
              <div><dt>叙事动作</dt><dd>{concept.motion}</dd></div>
              <div><dt>诚实风险</dt><dd>{concept.risk}</dd></div>
            </dl>
            <p className={styles.acceptance}>A 已被产品负责人选择为深化方向，当前为反馈返修候选；B、C 仅保留作历史对照。静态与动效仍需分开复验，这不代表冻结定稿或发布上线。</p>
            <a href={`?concept=${concept.id}&view=sample`}>打开独立手机样片</a>
          </aside>
        )}
      </section>
    </main>
  );
}
