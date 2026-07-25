const CONTRACT_VERSION = "SITES_GUIDED_INTAKE_CONTRACT_V1";
const MAX_REQUEST_BYTES = 16 * 1024;
const UPSTREAM_TIMEOUT_MS = 55_000;
const SESSION_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/;

type IntakeTurn = { question: string; answer: string };
type IntakeRequest = {
  contract_version: string;
  session_id: string;
  question_text: string;
  turns: IntakeTurn[];
  locale: "zh-CN";
};

function safeJson(payload: unknown, status: number): Response {
  return Response.json(payload, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
    },
  });
}

function upstreamUrl(): string | null {
  const raw = process.env.PYTHON_ENGINE_URL?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" && url.hostname !== "127.0.0.1" && url.hostname !== "localhost") return null;
    url.pathname = "/api/intake/v1/turn";
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return null;
  }
}

function validPayload(value: unknown): value is IntakeRequest {
  if (!value || typeof value !== "object") return false;
  const payload = value as Partial<IntakeRequest>;
  if (payload.contract_version !== CONTRACT_VERSION || payload.locale !== "zh-CN") return false;
  if (typeof payload.session_id !== "string" || !SESSION_ID_PATTERN.test(payload.session_id)) return false;
  if (typeof payload.question_text !== "string" || payload.question_text.trim().length < 6 || payload.question_text.trim().length > 160) return false;
  if (!Array.isArray(payload.turns) || payload.turns.length > 8) return false;
  return payload.turns.every((turn) => (
    turn && typeof turn.question === "string" && turn.question.trim().length > 0 && turn.question.length <= 240
    && typeof turn.answer === "string" && turn.answer.trim().length > 0 && turn.answer.length <= 1200
  ));
}

export async function POST(request: Request): Promise<Response> {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
  if (contentType !== "application/json") return safeJson({ error: "请求格式不受支持。" }, 415);
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) return safeJson({ error: "本次辨识内容过长。" }, 413);

  let payload: unknown;
  try {
    payload = JSON.parse(body);
  } catch {
    return safeJson({ error: "请求内容不是有效 JSON。" }, 400);
  }
  if (!validPayload(payload)) return safeJson({ error: "辨识内容不完整或格式有误。" }, 400);

  const url = upstreamUrl();
  const engineKey = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !engineKey) return safeJson({ error: "AI 辨识暂时未连接。" }, 503);

  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Abalo-Engine-Key": engineKey },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
    const result = await upstream.json().catch(() => null) as Record<string, unknown> | null;
    if (!result || result.session_id !== payload.session_id) {
      return safeJson({ error: "AI 辨识返回异常，请稍后再试。" }, 502);
    }
    if (!upstream.ok) return safeJson({ error: "AI 辨识暂时不可用，请稍后再试。" }, upstream.status >= 500 ? 503 : upstream.status);
    return safeJson(result, 200);
  } catch {
    return safeJson({ error: "AI 辨识连接超时，请稍后再试。" }, 503);
  }
}
