import {
  getOwnerPreviewBudgetSnapshot,
  recordOwnerPreviewResult,
  reserveOwnerPreviewAttempt,
} from "../../../../../db/owner-preview-budget";

const MAX_REQUEST_BYTES = 32 * 1024;
const MAX_RESPONSE_BYTES = 128 * 1024;
const UPSTREAM_TIMEOUT_MS = 100_000;

function safeJson(body: unknown, status: number): Response {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

function upstreamUrl(): URL | null {
  const raw = process.env.PYTHON_ENGINE_URL?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    const local = url.hostname === "127.0.0.1" || url.hostname === "localhost";
    if (url.protocol !== "https:" && !(local && url.protocol === "http:")) return null;
    url.pathname = `${url.pathname.replace(/\/$/, "")}/api/preview/v1/meihua`;
    url.search = "";
    url.hash = "";
    return url;
  } catch {
    return null;
  }
}

function isOwner(request: Request): boolean {
  const expectedOwner = process.env.ABALO_PREVIEW_OWNER_EMAIL?.trim().toLowerCase();
  const authenticatedOwner = request.headers.get("oai-authenticated-user-email")?.trim().toLowerCase();
  return Boolean(expectedOwner && authenticatedOwner && authenticatedOwner === expectedOwner);
}

export async function GET(request: Request): Promise<Response> {
  if (!isOwner(request)) return safeJson({ error: "此入口仅向所有者开放。" }, 403);
  try {
    const budget = await getOwnerPreviewBudgetSnapshot();
    return safeJson({
      status: budget.status,
      hard_limit_enabled: false,
      total_attempts: budget.reservedCalls,
      actual_total_usd: budget.actualMicroUsd / 1_000_000,
    }, 200);
  } catch {
    return safeJson({ error: "私有体验次数守门暂时不可用。" }, 503);
  }
}

export async function POST(request: Request): Promise<Response> {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
  if (contentType !== "application/json") return safeJson({ error: "请求格式不受支持。" }, 415);
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  let requestPayload: { contract_version?: unknown };
  try { requestPayload = JSON.parse(body) as { contract_version?: unknown }; } catch { return safeJson({ error: "请求内容不是有效 JSON。" }, 400); }
  if (requestPayload.contract_version !== "SITES_OWNER_PREVIEW_CONTRACT_V1") {
    return safeJson({ error: "请求版本不受支持。" }, 400);
  }

  if (process.env.ABALO_OWNER_PREVIEW_GATE_ENABLED?.trim().toLowerCase() !== "true") {
    return safeJson({ error: "新版解读私有体验尚未开放。" }, 503);
  }
  if (!isOwner(request)) {
    return safeJson({ error: "此入口仅向所有者开放。" }, 403);
  }

  const url = upstreamUrl();
  const engineKey = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !engineKey) return safeJson({ error: "新版解读私有体验尚未连接。" }, 503);
  try {
    await reserveOwnerPreviewAttempt();
  } catch {
    return safeJson({ error: "私有体验次数守门暂时不可用，未发起模型请求。" }, 503);
  }
  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Abalo-Engine-Key": engineKey },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
    const responseText = await upstream.text();
    if (new TextEncoder().encode(responseText).byteLength > MAX_RESPONSE_BYTES) return safeJson({ error: "新版解读响应异常。" }, 502);
    const payload = JSON.parse(responseText) as {
      contract_version?: unknown;
      status?: unknown;
      preview_meta?: { actual_api_cost_usd?: unknown };
    };
    if (payload.contract_version !== "SITES_OWNER_PREVIEW_CONTRACT_V1") {
      await recordOwnerPreviewResult("INVALID_UPSTREAM_RESPONSE", null);
      return safeJson({ error: "新版解读响应异常。" }, 502);
    }
    const actualCost = typeof payload.preview_meta?.actual_api_cost_usd === "number"
      ? payload.preview_meta.actual_api_cost_usd
      : null;
    const usage = await recordOwnerPreviewResult(typeof payload.status === "string" ? payload.status : "UNKNOWN", actualCost);
    return safeJson({
      ...payload,
      preview_meta: {
        ...payload.preview_meta,
        hard_limit_enabled: false,
        total_attempts: usage.reservedCalls,
        actual_total_usd: usage.actualMicroUsd / 1_000_000,
      },
    }, upstream.ok ? 200 : 502);
  } catch {
    try { await recordOwnerPreviewResult("UPSTREAM_ERROR", null); } catch { /* reservation remains consumed */ }
    return safeJson({ error: "新版解读服务正在唤醒，请稍后再试。" }, 503);
  }
}
