"use client";

import { useEffect } from "react";
import { castingViewport, type CastingViewport } from "./lib/casting-viewport";

export function PwaRuntime() {
  useEffect(() => {
    let casting: CastingViewport | null = null;
    const syncViewportHeight = () => {
      const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
      document.documentElement.style.setProperty("--app-height", `${Math.round(viewportHeight)}px`);
      casting = castingViewport(casting, window.innerWidth, viewportHeight,
        document.activeElement?.matches("input, textarea, [contenteditable=true]") ?? false);
      document.documentElement.style.setProperty("--casting-height", `${Math.round(casting.height)}px`);
      document.documentElement.dataset.castingKeyboard = String(casting.keyboardOpen);
    };

    syncViewportHeight();
    window.addEventListener("resize", syncViewportHeight, { passive: true });
    window.addEventListener("orientationchange", syncViewportHeight, { passive: true });
    window.addEventListener("pageshow", syncViewportHeight);
    document.addEventListener("visibilitychange", syncViewportHeight);
    document.addEventListener("focusin", syncViewportHeight);
    document.addEventListener("focusout", syncViewportHeight);
    window.visualViewport?.addEventListener("resize", syncViewportHeight, { passive: true });

    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
        // The core flow remains available if installation support is unavailable.
      });
    }

    return () => {
      window.removeEventListener("resize", syncViewportHeight);
      window.removeEventListener("orientationchange", syncViewportHeight);
      window.removeEventListener("pageshow", syncViewportHeight);
      document.removeEventListener("visibilitychange", syncViewportHeight);
      document.removeEventListener("focusin", syncViewportHeight);
      document.removeEventListener("focusout", syncViewportHeight);
      window.visualViewport?.removeEventListener("resize", syncViewportHeight);
    };
  }, []);

  return null;
}
