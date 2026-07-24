import { getRawDb } from ".";

export const PUBLIC_RATE_LIMIT_MAX_REQUESTS = 6;
export const PUBLIC_RATE_LIMIT_WINDOW_SECONDS = 60 * 60;
const PUBLIC_RATE_LIMIT_RETENTION_SECONDS = 7 * 24 * 60 * 60;

type RateLimitRequestRow = {
  subject_hash: string;
};

export type PublicRateLimitReservation = {
  allowed: boolean;
  isNewRequest: boolean;
};

function normalizedHexHash(subjectHash: string): string {
  const value = subjectHash.trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(value)) throw new Error("Invalid public rate-limit subject hash.");
  return value;
}

function normalizedRequestId(requestId: string): string {
  const value = requestId.trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(value)) {
    throw new Error("Invalid public rate-limit request id.");
  }
  return value;
}

async function ensureRateLimitTable(db: D1Database): Promise<void> {
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS public_request_rate_limits (
      request_id text PRIMARY KEY NOT NULL,
      subject_hash text NOT NULL,
      created_at text NOT NULL
    )`),
    db.prepare(
      "CREATE INDEX IF NOT EXISTS public_request_rate_limits_subject_created_idx ON public_request_rate_limits (subject_hash, created_at)",
    ),
  ]);
}

export async function reservePublicRequestRateLimit(
  subjectHash: string,
  requestId: string,
  now = new Date(),
): Promise<PublicRateLimitReservation> {
  const db = getRawDb();
  await ensureRateLimitTable(db);
  const normalizedSubject = normalizedHexHash(subjectHash);
  const normalizedRequest = normalizedRequestId(requestId);
  const createdAt = now.toISOString();
  const windowStart = new Date(now.getTime() - PUBLIC_RATE_LIMIT_WINDOW_SECONDS * 1_000).toISOString();
  const retentionStart = new Date(now.getTime() - PUBLIC_RATE_LIMIT_RETENTION_SECONDS * 1_000).toISOString();

  await db.prepare("DELETE FROM public_request_rate_limits WHERE created_at < ?").bind(retentionStart).run();
  const inserted = await db.prepare(`INSERT OR IGNORE INTO public_request_rate_limits (
      request_id, subject_hash, created_at
    )
    SELECT ?, ?, ?
    WHERE (
      SELECT COUNT(*) FROM public_request_rate_limits
      WHERE subject_hash = ? AND created_at >= ?
    ) < ?`).bind(
      normalizedRequest,
      normalizedSubject,
      createdAt,
      normalizedSubject,
      windowStart,
      PUBLIC_RATE_LIMIT_MAX_REQUESTS,
    ).run();
  if (Number(inserted.meta?.changes ?? 0) === 1) {
    return { allowed: true, isNewRequest: true };
  }

  const existing = await db.prepare(
    "SELECT subject_hash FROM public_request_rate_limits WHERE request_id = ?",
  ).bind(normalizedRequest).first<RateLimitRequestRow>();
  if (existing?.subject_hash === normalizedSubject) {
    return { allowed: true, isNewRequest: false };
  }
  return { allowed: false, isNewRequest: false };
}
