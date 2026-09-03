"use client";

import { useEffect, useState, type CSSProperties, type RefObject } from "react";

type MobileScrollPetalProps = {
  containerRef?: RefObject<HTMLElement | null>;
};

type ScrollPetalStyle = CSSProperties & {
  "--mobile-scroll-petal-progress": number;
};

export function MobileScrollPetal({ containerRef }: MobileScrollPetalProps) {
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const container = containerRef?.current ?? null;
    const scrollTarget: Window | HTMLElement = container ?? window;
    let frame = 0;

    const measure = () => {
      frame = 0;
      const scrollTop = container ? container.scrollTop : window.scrollY;
      const scrollHeight = container ? container.scrollHeight : document.documentElement.scrollHeight;
      const viewportHeight = container ? container.clientHeight : window.innerHeight;
      const travel = Math.max(0, scrollHeight - viewportHeight);
      setVisible(media.matches && travel > 24);
      setProgress(travel > 0 ? Math.min(1, Math.max(0, scrollTop / travel)) : 0);
    };

    const scheduleMeasure = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(measure);
    };

    scheduleMeasure();
    scrollTarget.addEventListener("scroll", scheduleMeasure, { passive: true });
    window.addEventListener("resize", scheduleMeasure);
    media.addEventListener("change", scheduleMeasure);

    const observationRoot = container ?? document.body ?? document.documentElement;
    const resizeObserver = new ResizeObserver(scheduleMeasure);
    resizeObserver.observe(observationRoot);
    const mutationObserver = new MutationObserver(scheduleMeasure);
    mutationObserver.observe(observationRoot, { childList: true, subtree: true });

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      scrollTarget.removeEventListener("scroll", scheduleMeasure);
      window.removeEventListener("resize", scheduleMeasure);
      media.removeEventListener("change", scheduleMeasure);
      resizeObserver.disconnect();
      mutationObserver.disconnect();
    };
  }, [containerRef]);

  return <span
    className={`mobile-scroll-petal ${containerRef ? "is-contained" : "is-viewport"}${visible ? " is-visible" : ""}`}
    style={{ "--mobile-scroll-petal-progress": progress } as ScrollPetalStyle}
    aria-hidden="true"
  >
    <img src="/casting-peony-petal-v1.png" alt="" />
  </span>;
}
