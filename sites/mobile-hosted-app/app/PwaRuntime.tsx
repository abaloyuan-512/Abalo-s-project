"use client";

import { useEffect } from "react";

export function PwaRuntime() {
  useEffect(() => {
    const syncViewportHeight = () => {
      const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
      document.documentElement.style.setProperty("--app-height", `${Math.round(viewportHeight)}px`);
    };

    syncViewportHeight();
    window.addEventListener("resize", syncViewportHeight, { passive: true });
    window.addEventListener("orientationchange", syncViewportHeight, { passive: true });
    window.addEventListener("pageshow", syncViewportHeight);
    document.addEventListener("visibilitychange", syncViewportHeight);
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
      window.visualViewport?.removeEventListener("resize", syncViewportHeight);
    };
  }, []);

  return null;
}
