import { and, desc, eq } from "drizzle-orm";
import { ensureProductSchema, getDb } from "../../../db";
import { observations } from "../../../db/schema";

const MAX_BODY_BYTES = 192 * 1024;
const TOKEN_PATTERN = /^[A-Za-z0-9_-]{32,160}$/;
const ID_PATTERN = /^[0-9a-f-]{36}$/i;

type SavePayload = {
  id?: string;
  question?: string;
  structured_intake?: unknown;
  numbers?: unknown;
  result?: unknown;
  action_text?: string;
  review_on?: string | null;
};

type ReviewPayload = {
  id?: string;
  reality_text?: string;
  learning_text?: string;
  action_text?: string;
  review_on?: string | null;
  status?: "OPEN" | "REVIEWED";
};

function json(body: unknown, status = 200) {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

function ownerToken(request: Request): string | null {
  const token = request.headers.get("x-guanxiang-key")?.trim() ?? "";
  return TOKEN_PATTERN.test(token) ? token : null;
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function readPayload<T>(request: Request): Promise<T | null> {
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_BODY_BYTES) return null;
  const raw = await request.text();
  if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) return null;
  try { return JSON.parse(raw) as T; } catch { return null; }
}

function cleanText(value: unknown, max: number): string {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

function cleanDate(value: unknown): string | null {
  if (value === null || value === "") return null;
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  return value;
}

function serialize(value: unknown, max: number): string | null {
  try {
    const encoded = JSON.stringify(value);
    return encoded.length <= max ? encoded : null;
  } catch {
    return null;
  }
}

function publicRecord(row: typeof observations.$inferSelect) {
  return {
    id: row.id,
    created_at: row.createdAt,
    updated_at: row.updatedAt,
    question: row.question,
    structured_intake: JSON.parse(row.intakeJson),
    numbers: JSON.parse(row.numbersJson),
    result: JSON.parse(row.resultJson),
    action_text: row.actionText,
    review_on: row.reviewOn,
    reality_text: row.realityText,
    learning_text: row.learningText,
    status: row.status,
  };
}

export async function GET(request: Request) {
  const token = ownerToken(request);
  if (!token) return json({ error: "无法识别这本观事簿。" }, 401);
  try {
    await ensureProductSchema();
    const ownerKeyHash = await sha256(token);
    const rows = await getDb().select().from(observations)
      .where(eq(observations.ownerKeyHash, ownerKeyHash))
      .orderBy(desc(observations.updatedAt)).limit(100);
    return json({ records: rows.map(publicRecord) });
  } catch {
    return json({ error: "观事簿暂时无法打开，请稍后再试。" }, 503);
  }
}

export async function POST(request: Request) {
  const token = ownerToken(request);
  if (!token) return json({ error: "无法识别这本观事簿。" }, 401);
  const payload = await readPayload<SavePayload>(request);
  const id = cleanText(payload?.id, 36);
  const question = cleanText(payload?.question, 160);
  const actionText = cleanText(payload?.action_text, 500);
  const intakeJson = serialize(payload?.structured_intake, 8_000);
  const numbersJson = serialize(payload?.numbers, 200);
  const resultJson = serialize(payload?.result, 120_000);
  if (!ID_PATTERN.test(id) || question.length < 6 || !actionText || !intakeJson || !numbersJson || !resultJson) {
    return json({ error: "保存内容不完整，请返回结果页重试。" }, 400);
  }
  try {
    await ensureProductSchema();
    const now = new Date().toISOString();
    const ownerKeyHash = await sha256(token);
    await getDb().insert(observations).values({
      id, ownerKeyHash, createdAt: now, updatedAt: now, question, intakeJson,
      numbersJson, resultJson, actionText, reviewOn: cleanDate(payload?.review_on),
    });
    const [row] = await getDb().select().from(observations)
      .where(and(eq(observations.id, id), eq(observations.ownerKeyHash, ownerKeyHash))).limit(1);
    return json({ record: publicRecord(row) }, 201);
  } catch (error) {
    const message = error instanceof Error ? error.message : "";
    if (message.includes("UNIQUE")) return json({ error: "这次观象已经保存。" }, 409);
    return json({ error: "这次观象暂时没有保存成功，请稍后再试。" }, 503);
  }
}

export async function PATCH(request: Request) {
  const token = ownerToken(request);
  if (!token) return json({ error: "无法识别这本观事簿。" }, 401);
  const payload = await readPayload<ReviewPayload>(request);
  const id = cleanText(payload?.id, 36);
  if (!ID_PATTERN.test(id)) return json({ error: "记录不存在。" }, 400);
  const values = {
    realityText: cleanText(payload?.reality_text, 2_000),
    learningText: cleanText(payload?.learning_text, 2_000),
    actionText: cleanText(payload?.action_text, 500),
    reviewOn: cleanDate(payload?.review_on),
    status: payload?.status === "REVIEWED" ? "REVIEWED" : "OPEN",
    updatedAt: new Date().toISOString(),
  };
  if (!values.actionText) return json({ error: "请保留一个可以验证的行动。" }, 400);
  try {
    await ensureProductSchema();
    const ownerKeyHash = await sha256(token);
    const [row] = await getDb().update(observations).set(values)
      .where(and(eq(observations.id, id), eq(observations.ownerKeyHash, ownerKeyHash))).returning();
    if (!row) return json({ error: "没有找到这条记录。" }, 404);
    return json({ record: publicRecord(row) });
  } catch {
    return json({ error: "复盘暂时没有保存成功，请稍后再试。" }, 503);
  }
}

export async function DELETE(request: Request) {
  const token = ownerToken(request);
  if (!token) return json({ error: "无法识别这本观事簿。" }, 401);
  const id = new URL(request.url).searchParams.get("id") ?? "";
  if (!ID_PATTERN.test(id)) return json({ error: "记录不存在。" }, 400);
  try {
    await ensureProductSchema();
    const ownerKeyHash = await sha256(token);
    await getDb().delete(observations)
      .where(and(eq(observations.id, id), eq(observations.ownerKeyHash, ownerKeyHash)));
    return json({ deleted: true });
  } catch {
    return json({ error: "暂时无法删除，请稍后再试。" }, 503);
  }
}
