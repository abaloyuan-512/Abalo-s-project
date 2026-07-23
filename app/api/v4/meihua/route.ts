import {
  getOwnerPreviewBudgetSnapshot,
  recordOwnerPreviewResult,
  reserveOwnerPreviewAttempt,
} from "../../../../db/owner-preview-budget";

const MAX_REQUEST_BYTES = 32 * 1024;
const MAX_RESPONSE_BYTES = 128 * 1024;
const POLL_UPSTREAM_TIMEOUT_MS = 15_000;
// Render's free instance can need 50+ seconds to wake. The initial POST must
// stay open long enough for the job to be created; later GET polls stay short.
const SUBMIT_UPSTREAM_TIMEOUT_MS = 90_000;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;

const PUBLIC_CONTRACT_VERSION = "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1";
const UPSTREAM_CONTRACT_VERSION = "SITES_OWNER_PREVIEW_CONTRACT_V1";

type PersonalizedPayload = {
  contract_version?: unknown;
  request_id?: unknown;
  status?: unknown;
  preview_meta?: { actual_api_cost_usd?: unknown };
  [key: string]: unknown;
};

function safeJson(body: unknown, status: number): Response {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

function upstreamUrl(path: string): URL | null {
  const raw = process.env.PYTHON_ENGINE_URL?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    const local = url.hostname === "127.0.0.1" || url.hostname === "localhost";
    if (url.protocol !== "https:" && !(local && url.protocol === "http:")) return null;
    url.pathname = `${url.pathname.replace(/\/$/, "")}${path}`;
    url.search = "";
    url.hash = "";
    return url;
  } catch {
    return null;
  }
}

function isAuthenticatedPreviewUser(request: Request): boolean {
  const authenticatedEmail = request.headers.get("oai-authenticated-user-email")?.trim();
  return Boolean(authenticatedEmail && authenticatedEmail.length <= 320);
}

function previewEnabled(): boolean {
  return process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED?.trim().toLowerCase() === "true";
}

async function readUpstream(upstream: Response): Promise<PersonalizedPayload | null> {
  const responseText = await upstream.text();
  if (new TextEncoder().encode(responseText).byteLength > MAX_RESPONSE_BYTES) return null;
  try {
    const payload = JSON.parse(responseText) as PersonalizedPayload;
    if (
      payload.contract_version !== UPSTREAM_CONTRACT_VERSION ||
      typeof payload.request_id !== "string" ||
      typeof payload.status !== "string"
    ) return null;
    return payload;
  } catch {
    return null;
  }
}

function publicPayload(payload: PersonalizedPayload): PersonalizedPayload {
  return { ...payload, contract_version: PUBLIC_CONTRACT_VERSION };
}

async function terminalResponse(requestId: string, payload: PersonalizedPayload): Promise<Response> {
  const actualCost = typeof payload.preview_meta?.actual_api_cost_usd === "number"
    ? payload.preview_meta.actual_api_cost_usd
    : null;
  const usage = await recordOwnerPreviewResult(
    requestId,
    typeof payload.status === "string" ? payload.status : "UNKNOWN",
    actualCost,
  );
  return safeJson({
    ...publicPayload(payload),
    preview_meta: {
      ...payload.preview_meta,
      hard_limit_enabled: false,
      total_attempts: usage.reservedCalls,
      actual_total_usd: usage.actualMicroUsd / 1_000_000,
      request_limit: usage.requestLimit,
      remaining_calls: usage.remainingCalls,
    },
  }, 200);
}

export async function GET(request: Request): Promise<Response> {
  if (!isAuthenticatedPreviewUser(request)) return safeJson({ error: "请先登录当前站点。" }, 403);
  const requestId = new URL(request.url).searchParams.get("request_id")?.trim();
  if (!requestId) {
    try {
      const budget = await getOwnerPreviewBudgetSnapshot();
      return safeJson({
        status: budget.status,
        hard_limit_enabled: false,
        total_attempts: budget.reservedCalls,
        actual_total_usd: budget.actualMicroUsd / 1_000_000,
        request_limit: budget.requestLimit,
        remaining_calls: budget.remainingCalls,
      }, 200);
    } catch {
      return safeJson({ error: "体验次数守门暂时不可用。" }, 503);
    }
  }
  if (!REQUEST_ID_PATTERN.test(requestId)) return safeJson({ error: "请求编号无效。" }, 400);
  if (!previewEnabled()) return safeJson({ error: "个性化解读服务尚未开放。" }, 503);
  const url = upstreamUrl(`/api/preview/v1/meihua/jobs/${encodeURIComponent(requestId)}`);
  const engineKey = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !engineKey) return safeJson({ error: "个性化解读服务尚未连接。" }, 503);
  try {
    const upstream = await fetch(url, {
      headers: { "X-Abalo-Engine-Key": engineKey },
      cache: "no-store",
      signal: AbortSignal.timeout(POLL_UPSTREAM_TIMEOUT_MS),
    });
    if (upstream.status === 404) return safeJson({ error: "生成任务尚未建立。" }, 404);
    const payload = await readUpstream(upstream);
    if (!payload || payload.request_id !== requestId) return safeJson({ error: "个性化解读响应异常。" }, 502);
    if (upstream.status === 202) return safeJson(publicPayload(payload), 202);
    if (!upstream.ok) return safeJson({ error: "个性化解读响应异常。" }, 502);
    return await terminalResponse(requestId, payload);
  } catch {
    return safeJson({ error: "生成仍在继续，页面会自动再次查询。" }, 503);
  }
}

export async function POST(request: Request): Promise<Response> {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
  if (contentType !== "application/json") return safeJson({ error: "请求格式不受支持。" }, 415);
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  let requestPayload: PersonalizedPayload;
  try { requestPayload = JSON.parse(body) as PersonalizedPayload; } catch { return safeJson({ error: "请求内容不是有效 JSON。" }, 400); }
  if (requestPayload.contract_version !== PUBLIC_CONTRACT_VERSION) {
    return safeJson({ error: "请求版本不受支持。" }, 400);
  }
  if (!previewEnabled()) return safeJson({ error: "个性化解读服务尚未开放。" }, 503);
  const requestId = typeof requestPayload.request_id === "string" ? requestPayload.request_id.trim() : "";
  if (!REQUEST_ID_PATTERN.test(requestId)) return safeJson({ error: "请求编号无效。" }, 400);
  if (!isAuthenticatedPreviewUser(request)) return safeJson({ error: "请先登录当前站点。" }, 403);

  const url = upstreamUrl("/api/preview/v1/meihua/jobs");
  const engineKey = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !engineKey) return safeJson({ error: "个性化解读服务尚未连接。" }, 503);
  let reservation: Awaited<ReturnType<typeof reserveOwnerPreviewAttempt>>;
  try {
    reservation = await reserveOwnerPreviewAttempt(requestId);
  } catch {
    return safeJson({ error: "体验次数守门暂时不可用，未发起模型请求。" }, 503);
  }
  if (!reservation.allowed) {
    if (reservation.requestState === "FINALIZED") {
      return safeJson({ error: "这个任务已经结束。为避免重复生成，请返回页面发起一个新任务。" }, 409);
    }
    return safeJson({ error: "使用记录暂时不可用，未发起模型请求。" }, 503);
  }
  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Abalo-Engine-Key": engineKey },
      body: JSON.stringify({
        ...requestPayload,
        contract_version: UPSTREAM_CONTRACT_VERSION,
        user_acknowledgements: {
          owner_preview_only: true,
          live_model_cost_acknowledged: true,
          no_formal_persistence: true,
          user_statements_not_verified_facts: true,
        },
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(SUBMIT_UPSTREAM_TIMEOUT_MS),
    });
    if (upstream.status === 409) {
      await recordOwnerPreviewResult(requestId, "REQUEST_ID_CONFLICT", 0);
      return safeJson({ error: "请求编号与已有任务冲突。" }, 409);
    }
    const payload = await readUpstream(upstream);
    if (!payload || payload.request_id !== requestId) return safeJson({ error: "个性化解读响应异常。" }, 502);
    if (upstream.status === 429) {
      await recordOwnerPreviewResult(requestId, "PREVIEW_BUSY", 0);
      return safeJson({ error: String(payload.error || "当前已有解读正在生成，请稍后再试。") }, 429);
    }
    if (upstream.status === 202) return safeJson(publicPayload(payload), 202);
    if (!upstream.ok) return safeJson({ error: "个性化解读响应异常。" }, 502);
    return await terminalResponse(requestId, payload);
  } catch {
    return safeJson({ error: "任务提交暂时未确认，页面会使用同一编号重试。" }, 503);
  }
}
