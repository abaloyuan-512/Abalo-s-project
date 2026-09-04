"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import webStyles from "../direct-reading-v2-preview/page.module.css";
import styles from "./page.module.css";

type StarDensity = "sparse" | "balanced" | "full";
type StarPoint = { left: number; top: number; tianShu?: boolean; synthetic?: boolean; ambient?: boolean };

const STAR_BURST_MS = 4200;

const WEB_BASE_STARS: readonly StarPoint[] = [
  { left: 17.9642, top: 9.4697, tianShu: true },
  { left: 20.582, top: 19.9023 },
  { left: 27.9199, top: 23.5849 },
  { left: 29.7428, top: 15.5029 },
  { left: 38.954, top: 16.1758 },
  { left: 44.3685, top: 13.8945, synthetic: true },
  { left: 49.832, top: 11.627 },
];

const AMBIENT_STARS: readonly StarPoint[] = [
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

const DENSITY_COUNT: Record<StarDensity, number> = {
  sparse: 20,
  balanced: 34,
  full: 48,
};

const PREVIEW_ANSWER = [
  "可以推进，但要保留现实承接。",
  "先核实关键条件，再作最终决定。",
] as const;

function readDensity(): StarDensity {
  if (typeof window === "undefined") return "balanced";
  const value = new URLSearchParams(window.location.search).get("stars");
  return value === "sparse" || value === "full" ? value : "balanced";
}

function chooseStarBurst(total: number): number[] {
  const count = Math.min(3, Math.max(1, Math.floor(Math.random() * 3) + 1));
  const remaining = Array.from({ length: total }, (_, index) => index);
  const selected: number[] = [];

  while (selected.length < count && remaining.length > 0) {
    const pick = Math.min(remaining.length - 1, Math.floor(Math.random() * remaining.length));
    selected.push(remaining.splice(pick, 1)[0]);
  }

  return selected;
}

function P9ExtendedStarField({ density }: { density: StarDensity }) {
  const stars = useMemo(
    () => [...WEB_BASE_STARS, ...AMBIENT_STARS.slice(0, DENSITY_COUNT[density])],
    [density],
  );
  const [activeStars, setActiveStars] = useState<readonly number[]>([]);

  useEffect(() => {
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const pageVisibility = () => document.visibilityState === "visible";
    let burstTimer: ReturnType<typeof setTimeout> | undefined;
    let clearTimer: ReturnType<typeof setTimeout> | undefined;

    const clearTimers = () => {
      if (burstTimer) window.clearTimeout(burstTimer);
      if (clearTimer) window.clearTimeout(clearTimer);
    };

    const scheduleBurst = () => {
      const pause = 700 + Math.random() * 1100;
      burstTimer = window.setTimeout(() => {
        if (!pageVisibility()) {
          scheduleBurst();
          return;
        }
        setActiveStars(chooseStarBurst(stars.length));
        clearTimer = window.setTimeout(() => {
          setActiveStars([]);
          scheduleBurst();
        }, STAR_BURST_MS);
      }, pause);
    };

    const syncMotion = () => {
      clearTimers();
      setActiveStars([]);
      if (!motionPreference.matches && pageVisibility()) scheduleBurst();
    };

    syncMotion();
    motionPreference.addEventListener("change", syncMotion);
    document.addEventListener("visibilitychange", syncMotion);

    return () => {
      clearTimers();
      motionPreference.removeEventListener("change", syncMotion);
      document.removeEventListener("visibilitychange", syncMotion);
    };
  }, [stars]);

  const activeSet = new Set(activeStars);

  return (
    <div className="page9StarField" aria-hidden="true" data-active-count={activeStars.length} data-total-count={stars.length}>
      {WEB_BASE_STARS.filter((star) => star.synthetic).map((star) => (
        <span
          key={`base-${star.left}-${star.top}`}
          className={`page9BaseSyntheticStar ${styles.starAsset}`}
          style={{
            left: `${star.left}%`,
            top: `${star.top}%`,
            "--page9-star-delay": "-1.9s",
            "--page9-star-duration": "3.8s",
          } as CSSProperties}
        />
      ))}
      {stars.map((star, index) => (
        <span
          key={`${star.left}-${star.top}`}
          className={`page9Star ${styles.starAsset}${star.tianShu ? " page9TianShu" : ""}${star.synthetic ? " page9SyntheticStar" : ""}${star.ambient ? ` ${styles.ambientStar}` : ""}`}
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

export default function P9MobileArtLabPage() {
  const [density, setDensity] = useState<StarDensity>("balanced");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const sync = () => setDensity(readDensity());
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  return (
    <main className={`${webStyles.offlineShell} ${styles.labShell}`} data-p9-star-density={density} data-extra-stars={DENSITY_COUNT[density]}>
      <section className="page9Finale" aria-labelledby="p9-title">
        <div className="page9ArtPlane" aria-hidden="true">
          <span className={`page9Backdrop ${styles.backdrop}`} />
          <P9ExtendedStarField density={density} />
        </div>

        <header className={`page9FinaleHeading ${styles.headingWithoutLabel}`}>
          <h2 id="p9-title" tabIndex={-1}>观象寄语</h2>
        </header>

        <div className="page9Answer" aria-label="本次答案排版样片">
          <p>{PREVIEW_ANSWER[0]}</p>
          <p>{PREVIEW_ANSWER[1]}</p>
        </div>

        <div className="page9FinaleActions" aria-label="继续追问或分享本次解卦">
          <button type="button" className="page9Continue" onClick={() => setNotice("独立候选尚未接入主流程。")}>继续追问</button>
          <button type="button" className="page9Share" onClick={() => setNotice("独立候选仅用于星光视觉验收。")}>分享解卦</button>
          <small><button type="button" className="page9BookLink" onClick={() => setNotice("独立候选未写入正式观事簿。")}>本次观象已为您保存，可以前往观事簿进行回看。</button></small>
        </div>

        <p className="page9Notice" role="status" aria-live="polite">{notice}</p>
      </section>
    </main>
  );
}
