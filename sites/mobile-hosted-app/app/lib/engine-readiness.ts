export function retryAfterSeconds(response: Response, now = Date.now()): number {
  const value = response.headers.get("retry-after")?.trim();
  const seconds = value && /^\d+$/.test(value) ? Number(value)
    : value ? Math.ceil((Date.parse(value) - now) / 1000) : 30;
  return Number.isFinite(seconds) ? Math.min(3600, Math.max(1, seconds)) : 30;
}

/** Read-only wake-up probe. Never replay a model POST, even after a timeout. */
export async function engineReadiness(
  url: URL,
  onProfiles?: (profiles: readonly unknown[]) => void,
): Promise<Response | null> {
  if (process.env.GUANXIANG_ENGINE_PREFLIGHT !== "true" && !onProfiles) return null;
  let seconds = 3;
  let limited = false;
  try {
    const health = await fetch(new URL("/healthz", url), {
      cache: "no-store", signal: AbortSignal.timeout(25_000), redirect: "error",
    });
    limited = health.status === 429;
    seconds = health.headers.has("retry-after") || limited ? retryAfterSeconds(health) : 3;
    const body = (health.ok ? await health.json().catch(() => null) : null) as {
      status?: unknown; service?: unknown; direct_reading_profiles?: unknown;
    } | null;
    if (body?.status === "ok" && body?.service === "abalo-authoritative-engine") {
      onProfiles?.(Array.isArray(body.direct_reading_profiles) ? body.direct_reading_profiles : []);
      return null;
    }
  } catch { /* A sleeping free service may outlive this probe. No model request was sent. */ }
  return Response.json({
    error_code: limited ? "ENGINE_RATE_LIMITED" : "ENGINE_WAKING",
    error: limited ? "解读服务暂时限流，请稍后再试；尚未提交成卦任务。"
      : "免费解读服务正在唤醒或暂时无法连接，请稍后再试；尚未提交成卦任务。",
    not_submitted: true, retryable: true, retry_after_seconds: seconds,
  }, { status: 503, headers: { "Cache-Control": "no-store", "Retry-After": String(seconds) } });
}

export function uncertainEngineResponse(upstream: Response): Response {
  const seconds = retryAfterSeconds(upstream);
  return Response.json({
    error: upstream.status === 429 ? "解读服务暂时限流，请稍后查询原任务；不会重复提交。"
      : "暂未收到有效的解读响应，请稍后查询原任务；不会重复提交。",
    submission_uncertain: true, retryable: false, retry_after_seconds: seconds,
  }, { status: 503, headers: { "Cache-Control": "no-store", "Retry-After": String(seconds) } });
}
