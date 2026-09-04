"use client";

import { useMemo, useState, useSyncExternalStore } from "react";
import styles from "./page.module.css";

type ConceptId = "crane-gap" | "garden-path" | "quiet-scroll";
type PreviewState = "ask" | "confirmed" | "p5";

type Concept = {
  id: ConceptId;
  name: string;
  thesis: string;
  composition: string;
  motion: string;
  rhythm: string;
  risk: string;
};

const concepts: Concept[] = [
  {
    id: "crane-gap",
    name: "鹤隙问心",
    thesis: "让仙鹤掠过的大片空白成为停顿，唯一问题像在云隙里被看清。",
    composition: "人物与菊坡沉在左下，题字竖立左上；问题、回答与唯一主动作沿右侧留白形成一条安静的阅读轴。",
    motion: "沿用网页端双鹤的缓慢游走：一远一近、振翅与升沉错开，转向时短暂切换回身帧；任务区始终不随之移动。",
    rhythm: "主鹤 48 秒、远鹤 56 秒各成一周，8 秒错峰；速度远慢于旧样片，像远景生气而不是提示动画。",
    risk: "留白最强，若鸿蒙浏览器实际可视高度明显小于 932px，底部跳过入口可能需要再上提。",
  },
  {
    id: "garden-path",
    name: "菊径入问",
    thesis: "以菊坡的斜势引导视线，从画中人物走到问题，再落到回答。",
    composition: "背景向下放大，菊径占据下半幅；问题悬在山与园的交界，输入区像一方未题字的纸面落在前景。",
    motion: "网页端同源双鹤在山菊上空缓行，近景菊影只作极小风动；提交时朱砂印色短暂加深，提示一次确认。",
    rhythm: "鹤行 48–56 秒一周，菊影 6.8 秒一息、幅度不超过 3px；提交反馈 420ms。",
    risk: "画意最浓，前景密度也最高；需真机确认户外亮度下问题文字与菊坡仍有足够对比。",
  },
  {
    id: "quiet-scroll",
    name: "半卷辨一",
    thesis: "把一次澄清收进一幅未完全展开的立卷，强调这里只辨一处，不开启多轮问答。",
    composition: "山菊人物成为右侧窄长画卷，左侧以题字和说明定气；问题横跨卷边，输入与动作落在卷尾。",
    motion: "卷内远雾缓慢横移，网页端同源双鹤从卷外绕入卷中；文字与控制始终稳定。",
    rhythm: "卷雾 8.4 秒一息，双鹤 48–56 秒一周；减少瞬时位移，优先保障 Pura 70 Ultra 的稳定性。",
    risk: "构图辨识度最高，也最偏离当前横幅裁切习惯；需产品负责人确认卷边是否仍属于既有画意的可接受延展。",
  },
];

const samplePrompt = "你想确认的是继续留在现在的岗位，还是接受眼前的新机会？";
const sampleFinalQuestion = "我是否应该接受眼前的新机会？";
function subscribeToLocation(callback: () => void) {
  window.addEventListener("popstate", callback);
  return () => window.removeEventListener("popstate", callback);
}

function useQueryState() {
  const search = useSyncExternalStore(subscribeToLocation, () => window.location.search, () => "");
  const query = new URLSearchParams(search);
  const requested = query.get("concept") as ConceptId | null;
  return {
    conceptId: requested && concepts.some((concept) => concept.id === requested) ? requested : "crane-gap",
    sampleOnly: query.get("view") === "sample",
    motionOn: query.get("motion") !== "static",
  } as const;
}

export default function P4MobileArtLabPage() {
  const queryState = useQueryState();
  const [conceptOverride, setConceptOverride] = useState<ConceptId | null>(null);
  const [previewState, setPreviewState] = useState<PreviewState>("ask");
  const [motionOverride, setMotionOverride] = useState<boolean | null>(null);
  const [sampleOverride, setSampleOverride] = useState<boolean | null>(null);
  const [answer, setAnswer] = useState("");
  const conceptId = conceptOverride ?? queryState.conceptId;
  const sampleOnly = sampleOverride ?? queryState.sampleOnly;
  const motionOn = motionOverride ?? queryState.motionOn;
  const concept = useMemo(() => concepts.find((item) => item.id === conceptId) ?? concepts[0], [conceptId]);

  function chooseConcept(next: ConceptId) {
    setConceptOverride(next);
    setPreviewState("ask");
    setAnswer("");
    const url = new URL(window.location.href);
    url.searchParams.set("concept", next);
    url.searchParams.delete("view");
    window.history.replaceState({}, "", url);
  }

  function confirmAnswer() {
    if (!answer.trim()) return;
    setPreviewState("confirmed");
  }

  function skipAnswer() {
    setAnswer("");
    setPreviewState("confirmed");
  }

  return (
    <main className={`${styles.lab}${sampleOnly ? ` ${styles.sampleOnly}` : ""}`}>
      {!sampleOnly && (
        <header className={styles.reviewHeader}>
          <div>
            <p>移动端视觉优化 · P4</p>
            <h1>辨识：三种手机端候选</h1>
            <span>430×932 仿真，优先华为 Pura 70 Ultra / 鸿蒙；待产品负责人真机验收</span>
          </div>
          <div className={styles.reviewActions}>
            <button type="button" aria-pressed={!motionOn} onClick={() => setMotionOverride(false)}>静态定帧</button>
            <button type="button" aria-pressed={motionOn} onClick={() => setMotionOverride(true)}>动效样片</button>
            <button type="button" onClick={() => setSampleOverride(true)}>专注查看</button>
          </div>
        </header>
      )}

      {!sampleOnly && (
        <nav className={styles.conceptNav} aria-label="P4 候选方案">
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
          <article
            className={`${styles.phone}${motionOn ? ` ${styles.motionOn}` : ` ${styles.motionOff}`}`}
            data-concept={conceptId}
            data-state={previewState}
            aria-label={`${concept.name}手机端样片`}
          >
            <div className={styles.scene} aria-hidden="true">
              <div className={styles.landscape} />
              <div className={styles.paperWash} />
              <div className={styles.gardenBreath}><i /><i /><i /></div>
              <div className={styles.cranes}>
                <span className={`${styles.crane} ${styles.craneLeading}`}>
                  <i className={styles.craneBank}>
                    <span className={`${styles.craneFacing} ${styles.craneFacingRight}`} />
                    <span className={`${styles.craneFacing} ${styles.craneFacingLeft}`} />
                    <span className={`${styles.craneTurn} ${styles.craneTurnRight}`} />
                    <span className={`${styles.craneTurn} ${styles.craneTurnLeft}`} />
                  </i>
                </span>
                <span className={`${styles.crane} ${styles.craneFollowing}`}>
                  <i className={styles.craneBank}>
                    <span className={`${styles.craneFacing} ${styles.craneFacingRight}`} />
                    <span className={`${styles.craneFacing} ${styles.craneFacingLeft}`} />
                    <span className={`${styles.craneTurn} ${styles.craneTurnRight}`} />
                    <span className={`${styles.craneTurn} ${styles.craneTurnLeft}`} />
                  </i>
                </span>
              </div>
            </div>

            <div className={styles.brand} aria-label="观象"><b>观</b><b>象</b><i aria-hidden="true">观</i></div>

            <header className={styles.pageHeading}>
              <h2>辨识</h2>
              <p>卜卦之前，<br />让我帮你把纷繁的念头<br />慢慢理清。</p>
            </header>

            <section className={styles.task} aria-label="单次澄清预览">
              {previewState === "ask" && (
                <>
                  <p className={styles.understanding}>对问题的不同理解，会让解卦指向不同对象。让我们确认一下。</p>
                  <div className={styles.question}>
                    <span className={styles.questionMark} aria-hidden="true" />
                    <p>{samplePrompt}</p>
                  </div>
                  <div className={styles.compose}>
                    <textarea
                      aria-label="回答唯一澄清问题"
                      value={answer}
                      maxLength={400}
                      onChange={(event) => setAnswer(event.target.value)}
                      placeholder="用自己的原话简短说明……"
                    />
                    <button className={styles.primaryAction} type="button" disabled={!answer.trim()} onClick={confirmAnswer}>
                      <i aria-hidden="true" />
                      <span>带着这句回答<br />进入第三步：定问</span>
                    </button>
                  </div>
                  <button className={styles.skip} type="button" onClick={skipAnswer}>跳过这一问，仍按原题继续</button>
                </>
              )}

              {previewState === "confirmed" && (
                <div className={styles.confirmed} role="status">
                  <p>有疑则问 · 无疑直行</p>
                  <h3>这一处已经确认</h3>
                  <span>原问题保持不变；下一步只需在心中确认它。</span>
                  <button className={styles.primaryAction} type="button" onClick={() => setPreviewState("p5")}><i aria-hidden="true" /><span>进入第三步：定问</span></button>
                </div>
              )}

              {previewState === "p5" && (
                <div className={styles.p5Bridge}>
                  <p>P5 衔接样片</p>
                  <h3>定问</h3>
                  <span>最终问题</span>
                  <blockquote>{sampleFinalQuestion}</blockquote>
                  <div className={styles.clarification}>
                    <span>本次辨识确认</span>
                    <p>{answer.trim() || "已选择按原题继续。"}</p>
                  </div>
                  <button className={styles.primaryAction} type="button" onClick={() => { setPreviewState("ask"); setAnswer(""); }}><i aria-hidden="true" /><span>返回 P4 样片</span></button>
                </div>
              )}
            </section>
          </article>
        </div>

        {!sampleOnly && (
          <aside className={styles.notes}>
            <p>当前候选</p>
            <h2>{concept.name}</h2>
            <dl>
              <div><dt>构图逻辑</dt><dd>{concept.composition}</dd></div>
              <div><dt>叙事作用</dt><dd>{concept.motion}</dd></div>
              <div><dt>动效节奏</dt><dd>{concept.rhythm}</dd></div>
              <div><dt>诚实风险</dt><dd>{concept.risk}</dd></div>
            </dl>
            <p className={styles.acceptance}>候选完成不等于产品验收、冻结定稿或发布上线。当前不接入主流程；交互只用于验证 P4 单次澄清与 P5 衔接。</p>
            <a href={`?concept=${concept.id}&view=sample`} onClick={(event) => { event.preventDefault(); setSampleOverride(true); }}>打开独立手机样片</a>
          </aside>
        )}
      </section>

      {sampleOverride === true && <button className={styles.exitSample} type="button" onClick={() => setSampleOverride(false)}>退出专注查看</button>}
    </main>
  );
}
