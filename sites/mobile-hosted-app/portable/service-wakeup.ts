/** Only disclose the public Render health URL, never arbitrary/internal URLs or credentials. */
export function publicEngineHealthUrl(raw: string | undefined): string | null {
  if (!raw) return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" || !url.hostname.endsWith(".onrender.com") ||
        url.username || url.password || url.port || url.search || url.hash ||
        !["", "/"].includes(url.pathname)) return null;
    return new URL("/healthz", url).href;
  } catch { return null; }
}
