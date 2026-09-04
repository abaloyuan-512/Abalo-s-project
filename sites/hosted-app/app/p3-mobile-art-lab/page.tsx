"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import styles from "./page.module.css";

type Direction = {
  name: string;
  thesis: string;
  composition: string;
  motion: string;
  risk: string;
};

const direction: Direction = {
  name: "松瀑问心",
  thesis: "让老松从画外斜入，以一段枝势稳住近景；远峰只承接丝带般下泻的流云。",
  composition: "参考网页端的画外松枝：松枝从左侧进入并向画心舒展，不再暴露根石；远峰留在右侧，题名和书写占据中部纸白。",
  motion: "松枝沿用原始轻摆逻辑，幅度只提高约四成，周期由 7.6 秒微调为 6.8 秒；云瀑保持真实水墨静态层。",
  risk: "WebGL 与松树持续微动需要在华为 Pura 70 Ultra 真机确认帧率、功耗与鸿蒙浏览器合成表现。",
};

function subscribeToLocation(callback: () => void) {
  window.addEventListener("popstate", callback);
  return () => window.removeEventListener("popstate", callback);
}

function usePreviewState() {
  const search = useSyncExternalStore(subscribeToLocation, () => window.location.search, () => "");
  const query = new URLSearchParams(search);
  const [sampleOverride, setSampleOverride] = useState<boolean | null>(null);
  const [motionOverride, setMotionOverride] = useState<boolean | null>(null);

  return {
    sampleOnly: sampleOverride ?? query.get("view") === "sample",
    setSampleOnly: setSampleOverride,
    motionOn: motionOverride ?? query.get("motion") !== "static",
    setMotionOn: setMotionOverride,
  };
}

export default function P3MobileArtLabPage() {
  const { sampleOnly, setSampleOnly, motionOn, setMotionOn } = usePreviewState();
  const [question, setQuestion] = useState("");
  const [checking, setChecking] = useState(false);
  const checkingTimer = useRef<number | null>(null);
  const questionLength = question.trim().length;

  useEffect(() => () => {
    if (checkingTimer.current !== null) window.clearTimeout(checkingTimer.current);
  }, []);

  function confirmQuestion() {
    if (questionLength < 6 || checking) return;
    setChecking(true);
    checkingTimer.current = window.setTimeout(() => {
      checkingTimer.current = null;
    }, 900);
  }

  function updateQuestion(value: string) {
    if (checkingTimer.current !== null) {
      window.clearTimeout(checkingTimer.current);
      checkingTimer.current = null;
    }
    setQuestion(value);
    setChecking(false);
  }

  return (
    <main className={`${styles.lab}${sampleOnly ? ` ${styles.sampleOnly}` : ""}`}>
      {!sampleOnly && (
        <header className={styles.reviewHeader}>
          <div>
            <p>移动端视觉优化 · P3</p>
            <h1>正问：松瀑合境返修</h1>
            <span>华为 Pura 70 Ultra 430×932 近似仿真，待产品负责人真机验收</span>
          </div>
          <div className={styles.reviewActions}>
            <button type="button" aria-pressed={!motionOn} onClick={() => setMotionOn(false)}>静态定帧</button>
            <button type="button" aria-pressed={motionOn} onClick={() => setMotionOn(true)}>动效样片</button>
            <button type="button" onClick={() => setSampleOnly(true)}>专注查看</button>
          </div>
        </header>
      )}

      <section className={styles.reviewBody}>
        <article
          className={`${styles.phone}${motionOn ? ` ${styles.motionOn}` : ` ${styles.motionOff}`}`}
          aria-label={`${direction.name}手机端样片`}
        >
          <div className={styles.scene} aria-hidden="true">
            <img className={`${styles.landscape} ${styles.mountain}`} src="/question-cloudfall-base-v6.png" alt="" />
            <img className={styles.pine} src="/question-pine-tree-v2.png" alt="" />
            <span className={styles.paperWash} />
          </div>

          <div className={styles.brand} aria-label="观象"><b>观</b><b>象</b><i aria-hidden="true">观</i></div>

          <section className={styles.stage} aria-labelledby="p3-lab-title">
            <header className={styles.heading}>
              <p>观象之法 · 壹</p>
              <h2 id="p3-lab-title">正问</h2>
            </header>

            <div className={styles.writing}>
              <label htmlFor="p3-lab-question">此刻，你想问的是什么？</label>
              <textarea
                id="p3-lab-question"
                aria-label="你想问的问题"
                aria-describedby="p3-lab-guidance p3-lab-count"
                placeholder="请把你的问题写在这里……"
                value={question}
                maxLength={160}
                onChange={(event) => updateQuestion(event.target.value)}
              />
              <div className={styles.meta}>
                <p id="p3-lab-guidance">不必担心问得是否准确。<br />写下之后，系统只在必要时请你辨清一处歧义。</p>
                <span id="p3-lab-count" aria-live="polite">{questionLength} / 160</span>
              </div>
            </div>

            <div className={`${styles.advance}${questionLength >= 6 && !checking ? ` ${styles.ready}` : ""}`}>
              <button type="button" disabled={questionLength < 6 || checking} onClick={confirmQuestion}>
                <span>{checking ? "正在判断是否需要辨识" : <span>问题已经写好<br />继续</span>}</span>
                <i aria-hidden="true" />
              </button>
              <p role="status" aria-live="polite">
                {questionLength > 0 && questionLength < 6
                  ? "请再写详细一点，让我更清楚你想问的是什么。"
                  : checking
                    ? "系统正在判断是否存在会影响解卦的歧义。"
                    : ""}
              </p>
            </div>
          </section>
        </article>

        {!sampleOnly && (
          <aside className={styles.notes}>
            <p>当前候选</p>
            <h2>{direction.name}</h2>
            <dl>
              <div><dt>构图逻辑</dt><dd>{direction.composition}</dd></div>
              <div><dt>叙事动作</dt><dd>{direction.motion}</dd></div>
              <div><dt>诚实风险</dt><dd>{direction.risk}</dd></div>
            </dl>
            <p className={styles.acceptance}>当前仅为候选完成，不代表产品验收、冻结定稿或发布上线。主流程、P1 与冻结网站均未接入。</p>
            <a href="?view=sample">打开独立手机样片</a>
          </aside>
        )}
      </section>
    </main>
  );
}
