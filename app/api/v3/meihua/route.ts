const MAX_REQUEST_BYTES = 16 * 1024;
const MAX_RESPONSE_BYTES = 128 * 1024;
const UPSTREAM_TIMEOUT_MS = 90_000;

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
    url.pathname = `${url.pathname.replace(/\/$/, "")}/api/v3/meihua`;
    url.search = "";
    url.hash = "";
    return url;
  } catch {
    return null;
  }
}

export async function POST(request: Request): Promise<Response> {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
  if (contentType !== "application/json") return safeJson({ error: "请求格式不受支持。" }, 415);
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  try { JSON.parse(body); } catch { return safeJson({ error: "请求内容不是有效 JSON。" }, 400); }

  const url = upstreamUrl();
  const engineKey = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !engineKey) return safeJson({ error: "排盘服务尚未连接，请稍后再试。" }, 503);
  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Abalo-Engine-Key": engineKey },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
    const responseText = await upstream.text();
    if (new TextEncoder().encode(responseText).byteLength > MAX_RESPONSE_BYTES) return safeJson({ error: "排盘服务响应异常。" }, 502);
    const payload = JSON.parse(responseText) as { contract_version?: unknown };
    if (payload.contract_version !== "SITES_MEIHUA_API_CONTRACT_V3") return safeJson({ error: "排盘服务响应异常。" }, 502);
    return safeJson(payload, upstream.ok ? 200 : 502);
  } catch {
    return safeJson({ error: "排盘引擎正在唤醒，请稍后再试。" }, 503);
  }
}
