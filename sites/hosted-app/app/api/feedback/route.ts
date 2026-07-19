import { ensureProductSchema, getDb } from "../../../db";
import { feedback } from "../../../db/schema";

const KINDS = new Set(["体验建议", "内容纠错", "排盘异常", "其他"]);

export async function POST(request: Request) {
  const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim();
  if (contentType !== "application/json") return Response.json({ error: "请求格式不受支持。" }, { status: 415 });
  const raw = await request.text();
  if (new TextEncoder().encode(raw).byteLength > 12 * 1024) return Response.json({ error: "反馈内容过长。" }, { status: 413 });
  let payload: { kind?: unknown; content?: unknown; contact?: unknown; page?: unknown };
  try { payload = JSON.parse(raw) as typeof payload; } catch { return Response.json({ error: "反馈格式不正确。" }, { status: 400 }); }
  const kind = typeof payload.kind === "string" && KINDS.has(payload.kind) ? payload.kind : "其他";
  const content = typeof payload.content === "string" ? payload.content.trim().slice(0, 2_000) : "";
  const contact = typeof payload.contact === "string" ? payload.contact.trim().slice(0, 160) : "";
  const page = typeof payload.page === "string" ? payload.page.trim().slice(0, 200) : "/";
  if (content.length < 6) return Response.json({ error: "请至少写下六个字，帮助我们理解问题。" }, { status: 400 });
  try {
    await ensureProductSchema();
    await getDb().insert(feedback).values({ id: crypto.randomUUID(), createdAt: new Date().toISOString(), kind, content, contact: contact || null, page });
    return Response.json({ saved: true }, { status: 201, headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ error: "反馈暂时没有送达，请稍后再试。" }, { status: 503 });
  }
}
