"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import styles from "./page.module.css";

const BASE_ART = "/p1-motion-pre-reveal-base-v2.png";
const FINAL_ART = "/p1-motion-ink-realm-v1.png";
const SELECTED_MOTION = "/p1-mobile-motion-selected-v1.mp4";

export default function P1MotionPreview() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [motionEnabled, setMotionEnabled] = useState<boolean | null>(null);
  const [videoReady, setVideoReady] = useState(false);
  const [settled, setSettled] = useState(false);
  const [entering, setEntering] = useState(false);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const applyPreference = () => {
      const enabled = !preference.matches;
      setMotionEnabled(enabled);
      setSettled(!enabled);
      setVideoReady(false);
    };

    applyPreference();
    preference.addEventListener("change", applyPreference);
    return () => preference.removeEventListener("change", applyPreference);
  }, []);

  const revealFilm = () => {
    setVideoReady(true);
    void videoRef.current?.play().catch(() => setSettled(true));
  };

  const enter = () => {
    if (!settled || entering) return;
    setEntering(true);
    window.setTimeout(() => setEntering(false), 680);
  };

  return (
    <main className={styles.study}>
      <section
        className={`${styles.stage}${videoReady ? ` ${styles.isPlaying}` : ""}${settled ? ` ${styles.isSettled}` : ""}${entering ? ` ${styles.isEntering}` : ""}`}
        aria-labelledby="p1-motion-title"
      >
        <h1 id="p1-motion-title" className={styles.srOnly}>观象</h1>

        <Image
          className={styles.baseArtwork}
          src={BASE_ART}
          alt=""
          fill
          priority
          unoptimized
          sizes="100vw"
          draggable={false}
        />

        {motionEnabled ? (
          <video
            ref={videoRef}
            className={styles.motionFilm}
            src={SELECTED_MOTION}
            muted
            playsInline
            preload="auto"
            onCanPlay={revealFilm}
            onEnded={() => setSettled(true)}
            onError={() => setSettled(true)}
            aria-hidden="true"
          />
        ) : null}

        <Image
          className={styles.finalArtwork}
          src={FINAL_ART}
          alt="水墨山水环抱观象题字，墨滴落入涟漪，小舟停泊于进入观象印圈之前"
          fill
          priority
          unoptimized
          sizes="100vw"
          draggable={false}
        />

        <button
          type="button"
          className={styles.enterHotspot}
          aria-label="进入观象"
          aria-disabled={!settled}
          onClick={enter}
        />

        <p className={styles.srOnly} aria-live="polite">
          {settled ? "水墨画境已经展开，可以进入观象" : "墨滴正在落入水面，水墨画境正在展开"}
        </p>
      </section>
    </main>
  );
}
