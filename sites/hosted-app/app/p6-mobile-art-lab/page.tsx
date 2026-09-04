"use client";

/* eslint-disable @next/next/no-img-element -- preserve the source page's layered petal animation without image-wrapper layout changes */

import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import styles from "./page.module.css";

const breaths = [
  { numeral: "一息", guidance: "输入第一个数", placeholder: "上卦", flower: "/casting-peony-bloom-1-v1.png" },
  { numeral: "二息", guidance: "输入第二个数", placeholder: "下卦", flower: "/casting-peony-bloom-2-v1.png" },
  { numeral: "三息", guidance: "输入第三个数", placeholder: "动爻", flower: "/casting-peony-bloom-3-v1.png" },
] as const;

const sourceWidth = 1440;
const sourceHeight = 900;

const petalMotions = [
  { left: 12, midX: -7, travelX: -34, travelY: 32, spin: -420, flipX: 540, flipY: -360, size: 10, duration: 8.8, delay: -1.1 },
  { left: 19, midX: -13, travelX: -44, travelY: 43, spin: 610, flipX: -720, flipY: 540, size: 16, duration: 19.6, delay: -8.7 },
  { left: 25, midX: -5, travelX: -38, travelY: 51, spin: -760, flipX: 900, flipY: 360, size: 27, duration: 14.8, delay: -4.4 },
  { left: 32, midX: -18, travelX: -52, travelY: 37, spin: 530, flipX: 450, flipY: -810, size: 13, duration: 10.4, delay: -11.8 },
  { left: 38, midX: -10, travelX: -47, travelY: 48, spin: -350, flipX: -630, flipY: 720, size: 72, duration: 22.4, delay: -6.3 },
  { left: 44, midX: -22, travelX: -61, travelY: 45, spin: 820, flipX: 1080, flipY: -540, size: 19, duration: 16.2, delay: -13.7 },
  { left: 50, midX: -8, travelX: -42, travelY: 35, spin: -580, flipX: 720, flipY: 450, size: 23, duration: 9.6, delay: -2.9 },
  { left: 56, midX: -15, travelX: -55, travelY: 53, spin: 460, flipX: -900, flipY: 810, size: 12, duration: 20.8, delay: -15.4 },
  { left: 62, midX: -4, travelX: -36, travelY: 41, spin: -910, flipX: 1260, flipY: -720, size: 30, duration: 13.1, delay: -9.6 },
  { left: 68, midX: -20, travelX: -64, travelY: 50, spin: 690, flipX: -540, flipY: 1080, size: 15, duration: 18.6, delay: -5.2 },
  { left: 74, midX: -11, travelX: -49, travelY: 39, spin: -480, flipX: 810, flipY: 630, size: 108, duration: 11.2, delay: -12.5 },
  { left: 81, midX: -24, travelX: -68, travelY: 47, spin: 940, flipX: -1080, flipY: -450, size: 20, duration: 21.5, delay: -7.4 },
  { left: 16, midX: -16, travelX: -57, travelY: 55, spin: 720, flipX: 630, flipY: -990, size: 25, duration: 17.8, delay: -16.2 },
  { left: 29, midX: -6, travelX: -41, travelY: 36, spin: -660, flipX: -810, flipY: 540, size: 11, duration: 8.5, delay: -3.7 },
  { left: 47, midX: -19, travelX: -59, travelY: 44, spin: 390, flipX: 990, flipY: -720, size: 84, duration: 15.4, delay: -10.9 },
  { left: 59, midX: -12, travelX: -46, travelY: 52, spin: -840, flipX: -1260, flipY: 810, size: 17, duration: 23.2, delay: -14.6 },
  { left: 72, midX: -26, travelX: -71, travelY: 42, spin: 570, flipX: 720, flipY: 1260, size: 28, duration: 12.5, delay: -1.9 },
  { left: 86, midX: -9, travelX: -43, travelY: 49, spin: -730, flipX: -900, flipY: -630, size: 14, duration: 19.9, delay: -8.1 },
] as const;

function petalStyle(motion: (typeof petalMotions)[number], breathIndex: number): CSSProperties {
  const sourceVw = sourceWidth / 100;
  const sourceVh = sourceHeight / 100;
  return {
    "--breath-delay": `${breathIndex * -1.6}s`,
    "--petal-delay": `${motion.delay}s`,
    "--petal-left": `${motion.left}%`,
    "--petal-quarter-x": `${motion.midX * 0.45 * sourceVw}px`,
    "--petal-mid-x": `${motion.midX * sourceVw}px`,
    "--petal-late-x": `${motion.travelX * 0.62 * sourceVw}px`,
    "--petal-travel-x": `${motion.travelX * sourceVw}px`,
    "--petal-quarter-y": `${motion.travelY * 0.17 * sourceVh}px`,
    "--petal-mid-y": `${motion.travelY * 0.4 * sourceVh}px`,
    "--petal-late-y": `${motion.travelY * 0.7 * sourceVh}px`,
    "--petal-travel-y": `${motion.travelY * sourceVh}px`,
    "--petal-quarter-spin": `${motion.spin * 0.18}deg`,
    "--petal-mid-spin": `${motion.spin * 0.43}deg`,
    "--petal-late-spin": `${motion.spin * 0.72}deg`,
    "--petal-spin": `${motion.spin}deg`,
    "--petal-quarter-flip-x": `${motion.flipX * 0.23}deg`,
    "--petal-mid-flip-x": `${motion.flipX * 0.48}deg`,
    "--petal-late-flip-x": `${motion.flipX * 0.76}deg`,
    "--petal-flip-x": `${motion.flipX}deg`,
    "--petal-quarter-flip-y": `${motion.flipY * 0.2}deg`,
    "--petal-mid-flip-y": `${motion.flipY * 0.46}deg`,
    "--petal-late-flip-y": `${motion.flipY * 0.74}deg`,
    "--petal-flip-y": `${motion.flipY}deg`,
    "--petal-size": `${motion.size}px`,
    "--petal-duration": `${motion.duration}s`,
  } as CSSProperties;
}

export default function P6MobileArtLab() {
  const [numbers, setNumbers] = useState(["", "", ""]);
  const [message, setMessage] = useState("");
  const [previewScale, setPreviewScale] = useState(1);

  useEffect(() => {
    function fitPreview() {
      setPreviewScale(Math.min(1, window.innerWidth / 430, window.innerHeight / 932));
    }

    fitPreview();
    window.addEventListener("resize", fitPreview);
    return () => window.removeEventListener("resize", fitPreview);
  }, []);

  function submitPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const valid = numbers.every((value) => /^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 999);
    setMessage(valid ? "本地视觉预览：数字已取好，未触发排盘。" : "请在三个位置，各输入一个1–999的整数。");
  }

  return (
    <main className={styles.lab} style={{ "--p6-preview-scale": previewScale } as CSSProperties}>
      <section className={styles.screen} aria-labelledby="p6-lab-title">
        <div className={styles.paperWash} aria-hidden="true" />
        <div className={styles.peonyScene} aria-hidden="true">
          <div className={styles.sceneCanvas}>
            <div className={styles.peonyBackdrop} />
            {breaths.map((breath, index) => (
              <span className={`${styles.bloom} ${styles[`bloom${index + 1}`]}`} key={breath.numeral}>
                <img src={breath.flower} alt="" />
              </span>
            ))}
            <div className={styles.petalLayer}>
              {breaths.map((breath, breathIndex) => (
                <span className={`${styles.petalOrigin} ${styles[`bloom${breathIndex + 1}`]}`} key={`petals-${breath.numeral}`}>
                  {petalMotions.map((motion, motionIndex) => (
                    <img className={styles.fallingPetal} src="/casting-peony-petal-v1.png" alt="" key={`${breath.numeral}-${motionIndex}`} style={petalStyle(motion, breathIndex)} />
                  ))}
                </span>
              ))}
            </div>
            <img className={`${styles.restingPetal} ${styles.restingPetal1}`} src="/casting-peony-petal-v1.png" alt="" />
            <img className={`${styles.restingPetal} ${styles.restingPetal2}`} src="/casting-peony-petal-v1.png" alt="" />
            <img className={`${styles.restingPetal} ${styles.restingPetal3}`} src="/casting-peony-petal-v1.png" alt="" />
          </div>
        </div>

        <div className={styles.brand} aria-label="观象"><b>观象</b><i>观</i></div>

        <form className={styles.composition} onSubmit={submitPreview} noValidate>
          <header className={styles.heading}>
            <p className={styles.eyebrow}>观象之法 · 肆</p>
            <h1 id="p6-lab-title">成卦</h1>
            <p className={styles.contemplation}><span>缓缓做三次呼吸</span><span>每一息结束，凭第一直觉写下一个数</span></p>
          </header>

          <fieldset className={styles.numberField}>
            <legend>依三次呼吸取三个整数</legend>
            {breaths.map((breath, index) => (
              <label className={styles.breath} key={breath.numeral}>
                <span className={styles.breathCopy}><b>{breath.numeral}</b><small>{breath.guidance}</small></span>
                <input aria-label={`第${index + 1}个数字`} aria-describedby="p6-range-note" inputMode="numeric" min="1" max="999" placeholder={breath.placeholder} type="number" value={numbers[index]} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} />
              </label>
            ))}
          </fieldset>

          <p className={styles.rangeNote} id="p6-range-note">每次呼吸结束后，在右侧输入一个1–999的整数</p>
          <button className={styles.castButton} type="submit"><img src="/fuxi-bagua-taiji.svg" alt="" aria-hidden="true" /><span>三个数已经取好<br />开始成卦</span></button>
          <p className={styles.message} role="status" aria-live="polite">{message}</p>
        </form>

      </section>
    </main>
  );
}
