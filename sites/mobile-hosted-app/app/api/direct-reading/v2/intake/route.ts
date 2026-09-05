import { engineReadiness, retryAfterSeconds } from "../../../../lib/engine-readiness";
import {
  PUBLIC_RATE_LIMIT_MAX_REQUESTS,
  PUBLIC_RATE_LIMIT_WINDOW_SECONDS,
  publicRateLimitSubject,
  reservePublicRequestRateLimit,
} from "../../../../../db/public-request-rate-limit";

const MAX_REQUEST_BYTES = 4 * 1024;
const TIMEOUT_MS = 25_000;
const CONTRACT_VERSION = "SITES_CONDITIONAL_INTAKE_PRODUCT_V1";
const INTAKE_ID_PATTERN = /^intake-[a-f0-9]{16,64}$/;

function safeJson(body: unknown, status: number, headers: Record<string, string> = {}): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
      ...headers,
    },
  });
}

function isAuthenticatedOwner(request: Request): boolean {
  const url = new URL(request.url);
  const localBypass = process.env.ABALO_LOCAL_PREVIEW_BYPASS_AUTH?.trim().toLowerCase() === "true";
  if (localBypass && ["127.0.0.1", "localhost"].includes(url.hostname)) return true;
  const email = request.headers.get("oai-authenticated-user-email")?.trim();
  const owner = process.env.ABALO_PREVIEW_OWNER_EMAIL?.trim();
  return Boolean(email && owner && email.toLowerCase() === owner.toLowerCase());
}

function enabled(): boolean {
  return process.env.ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED?.trim().toLowerCase() === "true";
}

function publicBetaEnabled(): boolean {
  return process.env.ABALO_PUBLIC_BETA_ENABLED?.trim().toLowerCase() === "true";
}

function upstreamUrl(): URL | null {
  const raw = process.env.PYTHON_ENGINE_URL?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    const local = ["127.0.0.1", "localhost"].includes(url.hostname);
    if (url.protocol !== "https:" && !(local && url.protocol === "http:")) return null;
    url.pathname = `${url.pathname.replace(/\/$/, "")}/api/preview/v2/direct-reading/intake`;
    url.search = "";
    url.hash = "";
    return url;
  } catch { return null; }
}

function validQuestion(value: unknown): value is string {
  return typeof value === "string" && value === value.trim() && value.length >= 6 && value.length <= 160 && !/[\r\n]/.test(value);
}

export async function POST(request: Request): Promise<Response> {
  if (!publicBetaEnabled() && !isAuthenticatedOwner(request)) {
    return safeJson({ error: "请先登录私有预览。", terminal: true }, 403);
  }
  if (!enabled()) return safeJson({ error: "条件辨识预览尚未开启。", terminal: true }, 503);
  if (request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase() !== "application/json") {
    return safeJson({ error: "请求格式不受支持。" }, 415);
  }
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  let payload: Record<string, unknown>;
  try { payload = JSON.parse(body) as Record<string, unknown>; } catch { return safeJson({ error: "请求内容不是有效JSON。" }, 400); }
  if (
    payload.contract_version !== CONTRACT_VERSION ||
    typeof payload.intake_id !== "string" || !INTAKE_ID_PATTERN.test(payload.intake_id) ||
    !validQuestion(payload.original_question) ||
    Object.keys(payload).some((key) => !["contract_version", "intake_id", "original_question"].includes(key))
  ) return safeJson({ error: "辨识请求无效。" }, 400);
  const url = upstreamUrl();
  const key = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !key) return safeJson({ error: "条件辨识引擎尚未连接。" }, 503);
  const unavailable = await engineReadiness(url);
  if (unavailable) return unavailable;
  if (!isAuthenticatedOwner(request)) {
    const subjectHash = await publicRateLimitSubject(request, key, "conditional-intake-v2");
    if (!subjectHash) return safeJson({ error: "暂时无法确认访问来源，未发起模型请求。" }, 503);
    try {
      const rateLimit = await reservePublicRequestRateLimit(subjectHash, String(payload.intake_id));
      if (!rateLimit.allowed) {
        return safeJson({
          error: `同一网络每小时最多发起 ${PUBLIC_RATE_LIMIT_MAX_REQUESTS} 次辨识，请稍后再试。`,
        }, 429, { "Retry-After": String(PUBLIC_RATE_LIMIT_WINDOW_SECONDS) });
      }
    } catch {
      return safeJson({ error: "访问频率守门暂时不可用，未发起模型请求。" }, 503);
    }
  }
  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Abalo-Engine-Key": key },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (upstream.status === 429) return safeJson({
      error: "辨识服务暂时限流，本次未取得辨识结果。", fail_open: true,
    }, 503, { "Retry-After": String(retryAfterSeconds(upstream)) });
    const result = await upstream.json() as Record<string, unknown>;
    const status = result.status;
    const kind = result.ambiguity_kind;
    const prompt = result.clarification_prompt;
    const safe = (
      result.contract_version === CONTRACT_VERSION && result.intake_id === payload.intake_id &&
      (status === "PASS" || status === "ASK_ONCE") &&
      result.original_question_preserved === true && result.router_attempts === 1 && result.automatic_retries === 0 &&
      (status === "PASS"
        ? kind == null && prompt == null
        : ["SUBJECT", "DECISION_AXIS", "JUDGMENT_OBJECT"].includes(String(kind)) && typeof prompt === "string")
    );
    if (!upstream.ok || !safe) {
      console.error("conditional_intake_upstream_rejected", {
        upstream_status: upstream.status,
        response_status: typeof status === "string" ? status : "INVALID",
        failure_code: typeof result.failure_code === "string" ? result.failure_code : null,
        safe_shape: safe,
      });
      return safeJson({ error: "条件辨识暂时不可用；请直接进入解卦。", fail_open: true }, 503);
    }
    return safeJson({
      contract_version: CONTRACT_VERSION,
      intake_id: result.intake_id,
      status,
      ambiguity_kind: kind ?? null,
      clarification_prompt: prompt ?? null,
      failure_code: typeof result.failure_code === "string" ? result.failure_code : null,
      router_attempts: 1,
      automatic_retries: 0,
    }, 200);
  } catch (error) {
    console.error("conditional_intake_upstream_fetch_failed", {
      error_name: error instanceof Error ? error.name : "UNKNOWN",
    });
    return safeJson({ error: "条件辨识暂时不可用；请直接进入解卦。", fail_open: true }, 503);
  }
}
