/** One user-initiated, credential-free wake-up. This does not submit questions or generate readings. */
export function createServiceWarmup(request: typeof fetch, now: () => number = Date.now): () => Promise<void> {
  let inFlight: Promise<void> | null = null;
  let lastAttempt = -Infinity;
  return () => {
    if (inFlight) return inFlight;
    if (now() - lastAttempt < 60_000) return Promise.resolve();
    lastAttempt = now();
    inFlight = (async () => {
      try {
        const config = await request("/api/service-wakeup", {
          credentials: "omit", cache: "no-store", signal: AbortSignal.timeout(5_000),
        });
        if (!config.ok) return; // The frozen Sites runtime does not expose this portable-only endpoint.
        const body = await config.json() as { health_url?: unknown };
        if (typeof body.health_url !== "string") return;
        const url = new URL(body.health_url);
        if (url.protocol !== "https:" || !url.hostname.endsWith(".onrender.com") ||
            url.username || url.password || url.port || url.pathname !== "/healthz" || url.search || url.hash) return;
        await request(url.href, {
          method: "GET", mode: "no-cors", credentials: "omit", referrerPolicy: "no-referrer",
          cache: "no-store", signal: AbortSignal.timeout(65_000),
        });
        // An opaque response cannot prove readiness. The server still checks health before any model POST.
      } catch { /* Server-side readiness remains authoritative; never retry a model call here. */ }
    })().finally(() => { inFlight = null; });
    return inFlight;
  };
}

export const warmReadingService = createServiceWarmup((input, init) => fetch(input, init));
