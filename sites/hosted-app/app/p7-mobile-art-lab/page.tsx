"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import styles from "./page.module.css";

type CandidateId = "heaven-heart" | "koi-orbit" | "scroll-colophon";
type PreviewId = CandidateId | "baseline";

type Candidate = {
  id: CandidateId;
  name: string;
  thesis: string;
  composition: string;
  motion: string;
  fishScale: string;
  risk: string;
};

const candidates: Candidate[] = [
  {
    id: "heaven-heart",
    name: "天心留白",
    thesis: "用巨幅太极的空处托住卦象，让成卦后的第一感受是静定，而不是信息堆叠。",
    composition: "六爻居于光明的视觉天心，卦序、卦名和入口沿中轴下行；双鲤只在边缘维持生命感。",
    motion: "太极近乎不可察地呼吸；双鲤沿用网页端分片摆尾、柔性转向与呼吸变速，叙事作用是让注意力收束到卦象。",
    fishScale: "墨鲤占屏宽 54% · 朱砂鲤占屏宽 55%",
    risk: "留白最克制，需真机确认鸿蒙浏览器工具栏出现时，底部入口仍有足够安全距离。",
  },
  {
    id: "koi-orbit",
    name: "游鱼绕卦",
    thesis: "让两尾锦鲤形成松散的阴阳回环，用游向而非装饰线把视线送到卦象和卦名。",
    composition: "六爻偏左上，卦序与卦名落在右下形成对角制衡，入口压住下方水平线。",
    motion: "双鲤沿用网页端分片摆尾、柔性转向与呼吸变速，太极保持静止；叙事作用是引导阅读顺序而不抢字。",
    fishScale: "墨鲤占屏宽 58% · 朱砂鲤占屏宽 68%",
    risk: "动势最强，必须在 Pura 70 Ultra 真机确认双鲤不会因高刷新率显得过快。",
  },
  {
    id: "scroll-colophon",
    name: "卷轴落款",
    thesis: "把六爻当作立轴画心，把卦名和入口当作题签与落款，建立手机独有的纵向张力。",
    composition: "六爻偏左贯穿中段，卦序与卦名垂落右上，入口像朱砂题记停在右下；不画卷框。",
    motion: "太极墨迹沿纵轴缓移，双鲤沿用网页端分片摆尾、柔性转向与呼吸变速；叙事作用是让画卷气息徐徐向下。",
    fishScale: "墨鲤占屏宽 71% · 朱砂鲤占屏宽 45%",
    risk: "偏轴最鲜明，360px 以下需继续验证卦名与六爻之间的呼吸宽度。",
  },
];

const taiLines = ["yin", "yin", "yin", "yang", "yang", "yang"] as const;

type KoiMotion = {
  x: number;
  y: number;
  heading: number;
  speed: number;
  baseSpeed: number;
  turnRate: number;
  targetX: number;
  targetY: number;
  retargetAt: number;
  phase: number;
  phaseRate: number;
  width: number;
  alpha: number;
};

const koiVisuals: Record<PreviewId, { inkWidth: number; cinnabarWidth: number; inkAlpha: number; cinnabarAlpha: number }> = {
  baseline: { inkWidth: 260, cinnabarWidth: 270, inkAlpha: .5, cinnabarAlpha: .56 },
  "heaven-heart": { inkWidth: 232, cinnabarWidth: 238, inkAlpha: .28, cinnabarAlpha: .24 },
  "koi-orbit": { inkWidth: 248, cinnabarWidth: 294, inkAlpha: .45, cinnabarAlpha: .53 },
  "scroll-colophon": { inkWidth: 304, cinnabarWidth: 192, inkAlpha: .32, cinnabarAlpha: .24 },
};

function P7KoiPond({ conceptId, motionOn }: { conceptId: PreviewId; motionOn: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    let frame = 0;
    let lastTime = performance.now();
    let visible = true;
    let width = 1;
    let height = 1;
    let redraw: (() => void) | null = null;
    let disposed = false;
    let seed = 711;
    const visual = koiVisuals[conceptId];
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const nextRandom = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };

    const loadImage = (src: string) => new Promise<HTMLImageElement>((resolve, reject) => {
      const image = new Image();
      image.decoding = "async";
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = src;
    });

    const randomTarget = (motion: KoiMotion, now: number) => {
      const marginX = Math.max(70, width * .08);
      const marginY = Math.max(60, height * .1);
      motion.targetX = marginX + nextRandom() * Math.max(1, width - marginX * 2);
      motion.targetY = marginY + nextRandom() * Math.max(1, height - marginY * 2);
      motion.retargetAt = now + 5200 + nextRandom() * 6200;
    };

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      width = Math.max(1, bounds.width);
      height = Math.max(1, bounds.height);
      const deviceScale = Math.min(window.devicePixelRatio || 1, 1.75);
      canvas.width = Math.round(width * deviceScale);
      canvas.height = Math.round(height * deviceScale);
      context.setTransform(deviceScale, 0, 0, deviceScale, 0, 0);
      redraw?.();
    };

    const normalizeAngle = (angle: number) => {
      let value = angle;
      while (value > Math.PI) value -= Math.PI * 2;
      while (value < -Math.PI) value += Math.PI * 2;
      return value;
    };

    const drawKoi = (image: HTMLImageElement, motion: KoiMotion) => {
      const drawWidth = motion.width * width / 430;
      const drawHeight = drawWidth * image.height / image.width;
      const slices = 36;
      const destinationSlice = drawWidth / slices;
      const tailAmplitude = drawWidth * .052;
      const breath = 1 + Math.sin(motion.phase * .45) * .012;

      context.save();
      context.translate(motion.x, motion.y);
      context.rotate(motion.heading + Math.sin(motion.phase * .34) * .018);
      context.scale(breath, 1 / breath);
      context.globalAlpha = motion.alpha;

      for (let index = 0; index < slices; index += 1) {
        const progress = (index + .5) / slices;
        const tailWeight = .14 + Math.pow(1 - progress, 1.75) * .86;
        const wave = Math.sin(motion.phase - progress * 5.2);
        const localY = wave * tailAmplitude * tailWeight;
        const nextProgress = Math.min(1, progress + 1 / slices);
        const nextTailWeight = .14 + Math.pow(1 - nextProgress, 1.75) * .86;
        const nextY = Math.sin(motion.phase - nextProgress * 5.2) * tailAmplitude * nextTailWeight;
        const localAngle = Math.atan2(nextY - localY, destinationSlice) * .72;
        const localX = -drawWidth / 2 + (index + .5) * destinationSlice;
        const clipX = -drawWidth / 2 + index * destinationSlice;

        context.save();
        context.beginPath();
        context.rect(clipX - .08, -drawHeight * 1.35, destinationSlice + .16, drawHeight * 2.7);
        context.clip();
        context.translate(localX, localY);
        context.rotate(localAngle);
        context.translate(-localX, 0);
        context.drawImage(image, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
        context.restore();
      }
      context.restore();
    };

    const updateMotion = (motion: KoiMotion, now: number, delta: number) => {
      const distance = Math.hypot(motion.targetX - motion.x, motion.targetY - motion.y);
      const edge = Math.max(42, Math.min(width, height) * .055);
      const nearEdge = motion.x < edge || motion.x > width - edge || motion.y < edge || motion.y > height - edge;
      if (now >= motion.retargetAt || distance < Math.max(70, width * .055) || nearEdge) randomTarget(motion, now);

      const desiredHeading = Math.atan2(motion.targetY - motion.y, motion.targetX - motion.x);
      const headingDelta = normalizeAngle(desiredHeading - motion.heading);
      const turn = Math.max(-motion.turnRate * delta, Math.min(motion.turnRate * delta, headingDelta));
      motion.heading += turn;
      const glide = motion.baseSpeed * (.9 + Math.sin(motion.phase * .24) * .1);
      motion.speed += (glide - motion.speed) * Math.min(1, delta * .55);
      motion.x += Math.cos(motion.heading) * motion.speed * delta;
      motion.y += Math.sin(motion.heading) * motion.speed * delta;
      motion.phase += motion.phaseRate * delta;
    };

    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    const visibilityObserver = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }, { rootMargin: "12%" });
    visibilityObserver.observe(canvas);

    Promise.all([
      loadImage("/page7-koi-cinnabar-v1.png"),
      loadImage("/page7-koi-ink-v1.png"),
    ]).then(([cinnabarKoi, inkKoi]) => {
      if (disposed) return;
      const now = performance.now();
      const motions: KoiMotion[] = [
        { x: width * .23, y: height * .78, heading: -.12, speed: 24, baseSpeed: 27, turnRate: .33, targetX: width * .7, targetY: height * .62, retargetAt: now + 4300, phase: .8, phaseRate: 3.35, width: visual.cinnabarWidth, alpha: visual.cinnabarAlpha },
        { x: width * .78, y: height * .24, heading: Math.PI + .1, speed: 21, baseSpeed: 24, turnRate: .29, targetX: width * .34, targetY: height * .35, retargetAt: now + 6600, phase: 3.7, phaseRate: 3.05, width: visual.inkWidth, alpha: visual.inkAlpha },
      ];

      redraw = () => {
        context.clearRect(0, 0, width, height);
        drawKoi(cinnabarKoi, motions[0]);
        drawKoi(inkKoi, motions[1]);
      };

      const draw = (time: number) => {
        if (disposed) return;
        const delta = Math.min(.04, Math.max(0, (time - lastTime) / 1000));
        lastTime = time;
        if (visible && !document.hidden) {
          if (motionOn && !reducedMotion.matches) motions.forEach((motion) => updateMotion(motion, time, delta));
          redraw?.();
        }
        if (motionOn && !reducedMotion.matches) frame = window.requestAnimationFrame(draw);
      };

      if (!motionOn || reducedMotion.matches) {
        motions[0].x = width * .2;
        motions[0].y = height * .78;
        motions[0].heading = -.1;
        motions[1].x = width * .8;
        motions[1].y = height * .25;
        motions[1].heading = Math.PI - .12;
        draw(now);
      } else {
        frame = window.requestAnimationFrame(draw);
      }
    }).catch(() => context.clearRect(0, 0, width, height));

    return () => {
      disposed = true;
      redraw = null;
      window.cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();
    };
  }, [conceptId, motionOn]);

  return <canvas ref={canvasRef} className={styles.koiPond} data-p7-koi-pond={conceptId} aria-hidden="true" />;
}

function subscribeToLocation(callback: () => void) {
  window.addEventListener("popstate", callback);
  return () => window.removeEventListener("popstate", callback);
}

function usePreviewState() {
  const search = useSyncExternalStore(subscribeToLocation, () => window.location.search, () => "");
  const query = new URLSearchParams(search);
  const requested = query.get("concept") as PreviewId | null;
  const validIds: PreviewId[] = ["baseline", ...candidates.map((candidate) => candidate.id)];
  const queryId = requested && validIds.includes(requested) ? requested : "koi-orbit";
  const [previewOverride, setPreviewOverride] = useState<PreviewId | null>(null);
  const [sampleOverride, setSampleOverride] = useState<boolean | null>(null);
  const [motionOverride, setMotionOverride] = useState<boolean | null>(null);

  return {
    previewId: previewOverride ?? queryId,
    setPreviewId: setPreviewOverride,
    sampleOnly: sampleOverride ?? query.get("view") === "sample",
    setSampleOnly: setSampleOverride,
    motionOn: motionOverride ?? query.get("motion") !== "static",
    setMotionOn: setMotionOverride,
    comparisonMode: query.get("view") === "motion-compare",
    motionLoop: query.get("motion") === "loop" || query.get("view") === "motion-compare",
  };
}

function BrushHexagram() {
  return (
    <div className={styles.hexagram} role="img" aria-label="泰卦卦象，三阴爻在上，三阳爻在下">
      {taiLines.map((line, index) => (
        <span key={`${line}-${index}`} className={`${styles.yao} ${line === "yin" ? styles.yin : styles.yang}`} aria-hidden="true">
          {line === "yang" ? (
            <img src="/page7-yao-brush-v1.png" alt="" />
          ) : (
            <><img src="/page7-yao-brush-short-v1.png" alt="" /><img src="/page7-yao-brush-short-v1.png" alt="" /></>
          )}
        </span>
      ))}
    </div>
  );
}

type P7PhoneProps = {
  conceptId: PreviewId;
  name: string;
  motionOn: boolean;
  motionLoop?: boolean;
  bridgeActive: boolean;
  titleId: string;
  onBridge: () => void;
};

function P7Phone({ conceptId, name, motionOn, motionLoop = false, bridgeActive, titleId, onBridge }: P7PhoneProps) {
  return (
    <article
      className={`${styles.phone}${motionOn ? ` ${styles.motionOn}` : ` ${styles.motionOff}`}${motionLoop ? ` ${styles.motionLoop}` : ""}${bridgeActive ? ` ${styles.bridgeActive}` : ""}`}
      aria-label={`${name}手机端样片`}
    >
      <div className={styles.scene} aria-hidden="true">
        <div className={styles.taiji} data-p7-taiji="true" />
        <P7KoiPond conceptId={conceptId} motionOn={motionOn} />
      </div>

      <section className={styles.cast} aria-labelledby={titleId}>
        <BrushHexagram />
        <div className={styles.summary}>
          <span className={styles.number}><i>第</i><b>11</b><i>卦</i></span>
          <h2 id={titleId}>泰</h2>
          <button type="button" aria-label="查看详细解卦，P8 衔接动效预览" onClick={onBridge}>查看详细解卦</button>
          <span className={styles.srOnly} role="status" aria-live="polite">{bridgeActive ? "已触发进入详细解卦的衔接动效预览" : ""}</span>
        </div>
      </section>
    </article>
  );
}

export default function P7MobileArtLabPage() {
  const { previewId, setPreviewId, sampleOnly, setSampleOnly, motionOn, setMotionOn, comparisonMode, motionLoop } = usePreviewState();
  const [bridgeActiveId, setBridgeActiveId] = useState<PreviewId | null>(null);
  const bridgeTimer = useRef<number | null>(null);
  const candidate = useMemo(
    () => candidates.find((item) => item.id === previewId) ?? candidates[1],
    [previewId],
  );

  useEffect(() => () => {
    if (bridgeTimer.current !== null) window.clearTimeout(bridgeTimer.current);
  }, []);

  function chooseCandidate(next: CandidateId) {
    setPreviewId(next);
    setBridgeActiveId(null);
    const url = new URL(window.location.href);
    url.searchParams.set("concept", next);
    url.searchParams.delete("view");
    window.history.replaceState({}, "", url);
  }

  function previewP8Bridge(id: PreviewId) {
    if (bridgeTimer.current !== null) window.clearTimeout(bridgeTimer.current);
    setBridgeActiveId(id);
    bridgeTimer.current = window.setTimeout(() => {
      setBridgeActiveId(null);
      bridgeTimer.current = null;
    }, 960);
  }

  if (comparisonMode) {
    return (
      <main className={`${styles.lab} ${styles.compareLab}`}>
        <header className={styles.compareHeader}>
          <p>移动端视觉优化 · P7</p>
          <h1>双鲤动态并排比较</h1>
          <span>三案均按 430×932 原尺寸呈现；游姿、转向与速度同源于网页端，动线同步，便于只比较鲤鱼大小与构图。</span>
        </header>
        <section className={styles.motionCompare} aria-label="P7 三个候选动态并排比较">
          {candidates.map((item, index) => (
            <article key={item.id} className={`${styles.compareItem} ${styles.conceptStage}`} data-concept={item.id}>
              <header>
                <p>{String.fromCharCode(65 + index)}</p>
                <h2>{item.name}</h2>
                <span>{item.fishScale}</span>
              </header>
              <P7Phone
                conceptId={item.id}
                name={item.name}
                motionOn
                motionLoop
                bridgeActive={bridgeActiveId === item.id}
                titleId={`p7-compare-${item.id}`}
                onBridge={() => previewP8Bridge(item.id)}
              />
            </article>
          ))}
        </section>
      </main>
    );
  }

  return (
    <main className={`${styles.lab} ${styles.conceptStage}${sampleOnly ? ` ${styles.sampleOnly}` : ""}`} data-concept={previewId}>
      {!sampleOnly && (
        <header className={styles.reviewHeader}>
          <div>
            <p>移动端视觉优化 · P7</p>
            <h1>卦象页独立美术实验</h1>
            <span>华为 Pura 70 Ultra / 鸿蒙尺寸仿真，待产品负责人真机验收</span>
          </div>
          <div className={styles.reviewActions}>
            <button type="button" aria-pressed={!motionOn} onClick={() => setMotionOn(false)}>静态定帧</button>
            <button type="button" aria-pressed={motionOn} onClick={() => setMotionOn(true)}>动效样片</button>
            <button type="button" onClick={() => setSampleOnly(true)}>专注查看</button>
          </div>
        </header>
      )}

      {!sampleOnly && (
        <nav className={styles.candidateNav} aria-label="P7 候选方案">
          {candidates.map((item) => (
            <button key={item.id} type="button" aria-pressed={item.id === previewId} onClick={() => chooseCandidate(item.id)}>
              <b>{item.name}</b>
              <span>{item.thesis}</span>
            </button>
          ))}
        </nav>
      )}

      <section className={styles.reviewBody}>
        <div className={styles.phoneColumn}>
          <P7Phone
            conceptId={previewId}
            name={previewId === "baseline" ? "现状基线" : candidate.name}
            motionOn={motionOn}
            motionLoop={motionLoop}
            bridgeActive={bridgeActiveId === previewId}
            titleId="p7-candidate-title"
            onBridge={() => previewP8Bridge(previewId)}
          />
        </div>

        {!sampleOnly && (
          <aside className={styles.notes}>
            <p>当前候选</p>
            <h2>{candidate.name}</h2>
            <dl>
              <div><dt>构图逻辑</dt><dd>{candidate.composition}</dd></div>
              <div><dt>叙事动作</dt><dd>{candidate.motion}</dd></div>
              <div><dt>诚实风险</dt><dd>{candidate.risk}</dd></div>
            </dl>
            <p className={styles.acceptance}>三个方案均为独立候选，未获产品负责人选择，不代表产品验收、冻结定稿、合并或发布上线。</p>
            <a href={`?concept=${candidate.id}&view=sample&motion=loop`}>打开循环动态手机样片</a>
          </aside>
        )}
      </section>
    </main>
  );
}
