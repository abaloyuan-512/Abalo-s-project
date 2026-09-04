"use client";

import { useMemo, useState, useSyncExternalStore } from "react";
import styles from "./page.module.css";

type ConceptId = "sunset-scroll" | "water-margin" | "reed-inscription";
type PreviewState = "ready" | "proposal";

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
    id: "sunset-scroll",
    name: "霞光横卷",
    thesis: "让问题横跨落霞与水岸，视线从定问题字直接落到最终所问，再沉到唯一入口。",
    composition: "题字与说明在上，最终问题占据中段最宽的一笔；辨识确认贴近问题，呼吸与入口在下方形成一次收束。",
    motion: "沿用网页端 P5 的三层景深：落霞 8.4 秒与 11.8 秒错拍流动，近远芦苇 5.2 秒与 6.8 秒随风，孤鹜 1.05 秒振翅、4.8 秒升沉；作用是让一幅活景把 P4 的纷念慢慢压静。",
    risk: "横向问题是主角，超过现有 160 字上限的异常数据不在本候选范围；仍需真机确认鸿蒙字体渲染。",
  },
  {
    id: "water-margin",
    name: "水际留白",
    thesis: "把水面留白变成确认区，让文字像题跋落在画外，避免任何卡片感。",
    composition: "定问竖题贴右岸，最终问题悬在中央水面；辨识确认压成低声旁注，入口落在画幅左下形成对角平衡。",
    motion: "保留网页端落霞、芦苇、孤鹜的错拍循环，但以更淡的天空叠层和更远的孤鹜维持水际留白；环境有风，问题始终不动。",
    risk: "右侧竖题最具手机专属性，若系统强制放大字体到 130% 以上，需要额外真机复验。",
  },
  {
    id: "reed-inscription",
    name: "苇岸题跋",
    thesis: "让芦苇成为左岸、文字成为右岸，以不对称双岸构图把最终问题托住。",
    composition: "定问沿左侧纵向落墨，最终问题与辨识确认在右侧错位排列；太极入口像画末印记落在右下，而不是一张按钮卡。",
    motion: "把网页端近远两层芦苇的 5.2 秒与 6.8 秒风动放到构图主岸，落霞在远处缓流，孤鹜振翅掠过题跋上方；以岸动衬字静。",
    risk: "偏轴构图对 360px 以下窄屏最敏感；本轮优先 430 × 932，并保留窄屏压缩规则。",
  },
];

const originalQuestion = "我和合伙人各自负责一个项目，现在应该暂停这个项目吗？";
const suggestedQuestion = "我目前负责、已经投入三个月的项目，现在应该暂停继续投入吗？";
const clarification = "是我目前负责、已经投入三个月的那个项目";

function subscribeToLocation(callback: () => void) {
  window.addEventListener("popstate", callback);
  return () => window.removeEventListener("popstate", callback);
}

function usePreviewQuery() {
  const search = useSyncExternalStore(subscribeToLocation, () => window.location.search, () => "");
  const query = new URLSearchParams(search);
  const requestedConcept = query.get("concept") as ConceptId | null;
  const requestedState = query.get("state") as PreviewState | null;
  return {
    queryConcept: requestedConcept && concepts.some((item) => item.id === requestedConcept) ? requestedConcept : concepts[0].id,
    queryState: requestedState === "proposal" ? "proposal" as const : "ready" as const,
    sampleOnly: query.get("view") === "sample",
    motionOn: query.get("motion") !== "static",
  };
}

function BaguaMark() {
  return <span className={styles.baguaMark} aria-hidden="true" />;
}

export default function P5MobileArtLabPage() {
  const query = usePreviewQuery();
  const [conceptOverride, setConceptOverride] = useState<ConceptId | null>(null);
  const [stateOverride, setStateOverride] = useState<PreviewState | null>(null);
  const [motionOverride, setMotionOverride] = useState<boolean | null>(null);
  const [sampleOverride, setSampleOverride] = useState<boolean | null>(null);
  const conceptId = conceptOverride ?? query.queryConcept;
  const previewState = stateOverride ?? query.queryState;
  const motionOn = motionOverride ?? query.motionOn;
  const sampleOnly = sampleOverride ?? query.sampleOnly;
  const [finalQuestion, setFinalQuestion] = useState(originalQuestion);
  const [confirmed, setConfirmed] = useState(false);
  const concept = useMemo(() => concepts.find((item) => item.id === conceptId) ?? concepts[0], [conceptId]);

  function chooseConcept(next: ConceptId) {
    setConceptOverride(next);
    setConfirmed(false);
    const url = new URL(window.location.href);
    url.searchParams.set("concept", next);
    window.history.replaceState({}, "", url);
  }

  function showState(next: PreviewState) {
    setStateOverride(next);
    setFinalQuestion(originalQuestion);
    setConfirmed(false);
    const url = new URL(window.location.href);
    url.searchParams.set("state", next);
    window.history.replaceState({}, "", url);
  }

  function decide(question: string) {
    setFinalQuestion(question);
    setStateOverride("ready");
    setConfirmed(false);
  }

  return (
    <main className={`${styles.lab}${sampleOnly ? ` ${styles.sampleOnly}` : ""}`} data-concept={conceptId}>
      {!sampleOnly && (
        <header className={styles.reviewHeader}>
          <div>
            <p>移动端视觉优化 · P5</p>
            <h1>定问：三种独立本地候选</h1>
            <span>华为 Pura 70 Ultra / 鸿蒙尺寸近似仿真，待产品负责人真机验收</span>
          </div>
          <div className={styles.reviewActions}>
            <button type="button" aria-pressed={!motionOn} onClick={() => setMotionOverride(false)}>静态定帧</button>
            <button type="button" aria-pressed={motionOn} onClick={() => setMotionOverride(true)}>动效样片</button>
            <button type="button" aria-pressed={previewState === "ready"} onClick={() => showState("ready")}>确认态</button>
            <button type="button" aria-pressed={previewState === "proposal"} onClick={() => showState("proposal")}>建议态</button>
            <button type="button" onClick={() => setSampleOverride(true)}>专注查看</button>
          </div>
        </header>
      )}

      {!sampleOnly && (
        <nav className={styles.conceptNav} aria-label="P5 候选方案">
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
            <div className={styles.scene} aria-hidden="true">
              <div className={styles.sceneImage} />
              <div className={styles.skyDrift} />
              <div className={styles.paperLight} />
              <span className={styles.bird} />
            </div>

            <div className={styles.brand} aria-label="观象"><b>观</b><b>象</b><i>观</i></div>

            <header className={styles.titleGroup}>
              <p>观象之法 · 叁</p>
              <h2>定问</h2>
              <span>收回纷乱的念头<br />确认你真正想问的事</span>
            </header>

            <section className={styles.workspace} aria-live="polite">
              {previewState === "proposal" ? (
                <div className={styles.proposal}>
                  <p>根据刚才的回答<br />你真正想确认的，也许更接近这一问：</p>
                  <blockquote>{suggestedQuestion}</blockquote>
                  <p>如果这句话更贴近你的心意，请采用这一问。<br />如果没有，请保留你最初的问题。</p>
                  <div>
                    <button type="button" onClick={() => decide(suggestedQuestion)}>采用建议</button>
                    <button type="button" onClick={() => decide(originalQuestion)}>保留原问</button>
                  </div>
                </div>
              ) : (
                <div className={styles.ready}>
                  <p>最终问题已经定下<br />接下来，请把注意力重新放回这一问</p>
                  <blockquote>{finalQuestion}</blockquote>
                  <div className={styles.clarification}>
                    <span>辨识确认</span>
                    <p>{clarification}</p>
                  </div>
                  <strong><span>请在心中再默念一遍最终问题</span><span>缓缓深呼吸</span></strong>
                </div>
              )}
            </section>

            {previewState === "ready" && (
              <div className={styles.readiness}>
                <button type="button" aria-pressed={confirmed} onClick={() => setConfirmed(true)}>
                  <BaguaMark />
                  <span>{confirmed ? "已经开始" : <><b>我已定问</b><small>进入第四步：成卦</small></>}</span>
                </button>
                <p role="status">{confirmed ? "独立样片已完成按钮反馈；未接入 P6。" : ""}</p>
              </div>
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
            <p className={styles.acceptance}>三案均为隔离本地候选。候选完成不等于产品验收、冻结定稿或发布上线；未经产品负责人选择，不接入主流程。</p>
            <a href={`?concept=${concept.id}&state=${previewState}&motion=${motionOn ? "on" : "static"}&view=sample`}>打开独立手机样片</a>
          </aside>
        )}
      </section>
    </main>
  );
}
