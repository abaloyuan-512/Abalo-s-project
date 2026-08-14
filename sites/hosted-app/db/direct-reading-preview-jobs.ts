import { getRawDb } from ".";

export type DirectReadingJobState = "NEW" | "RUNNING" | "FINALIZED" | "LOST" | "CONFLICT";

type JobRow = {
  payload_sha256: string;
  prompt_version: string;
  state: string;
  result_status: string | null;
};

export type DirectReadingJobSnapshot = {
  state: DirectReadingJobState;
  resultStatus: string | null;
};

function normalizedRequestId(requestId: string): string {
  const value = requestId.trim();
  if (!/^drv2-[a-f0-9]{16,64}$/.test(value)) throw new Error("Invalid direct reading request id.");
  return value;
}

function normalizedHash(value: string): string {
  const normalized = value.trim().toUpperCase();
  if (!/^[A-F0-9]{64}$/.test(normalized)) throw new Error("Invalid direct reading payload hash.");
  return normalized;
}

function normalizedPromptVersion(value: string): string {
  const normalized = value.trim();
  if (!/^[A-Z0-9_]{8,80}$/.test(normalized)) throw new Error("Invalid direct reading prompt version.");
  return normalized;
}

async function ensureTable(db: D1Database): Promise<void> {
  await db.prepare(`CREATE TABLE IF NOT EXISTS direct_reading_preview_jobs (
    request_id text PRIMARY KEY NOT NULL,
    payload_sha256 text NOT NULL,
    prompt_version text NOT NULL,
    state text DEFAULT 'RUNNING' NOT NULL,
    result_status text,
    created_at text NOT NULL,
    updated_at text NOT NULL
  )`).run();
}

async function readRow(db: D1Database, requestId: string): Promise<JobRow | null> {
  return db.prepare(`SELECT payload_sha256, prompt_version, state, result_status
    FROM direct_reading_preview_jobs WHERE request_id = ?`).bind(requestId).first<JobRow>();
}

function snapshot(row: JobRow): DirectReadingJobSnapshot {
  const state: DirectReadingJobState =
    row.state === "FINALIZED" ? "FINALIZED" : row.state === "LOST" ? "LOST" : "RUNNING";
  return { state, resultStatus: row.result_status };
}

export async function reserveDirectReadingPreviewJob(
  requestId: string,
  payloadSha256: string,
  promptVersion: string,
): Promise<DirectReadingJobSnapshot> {
  const db = getRawDb();
  await ensureTable(db);
  const id = normalizedRequestId(requestId);
  const digest = normalizedHash(payloadSha256);
  const prompt = normalizedPromptVersion(promptVersion);
  const now = new Date().toISOString();
  const inserted = await db.prepare(`INSERT OR IGNORE INTO direct_reading_preview_jobs (
    request_id, payload_sha256, prompt_version, state, result_status, created_at, updated_at
  ) VALUES (?, ?, ?, 'RUNNING', NULL, ?, ?)`).bind(id, digest, prompt, now, now).run();
  if (Number(inserted.meta?.changes ?? 0) === 1) return { state: "NEW", resultStatus: null };
  const existing = await readRow(db, id);
  if (!existing) throw new Error("Direct reading request row is unavailable.");
  if (existing.payload_sha256 !== digest || existing.prompt_version !== prompt) {
    return { state: "CONFLICT", resultStatus: existing.result_status };
  }
  return snapshot(existing);
}

export async function readDirectReadingPreviewJob(requestId: string): Promise<DirectReadingJobSnapshot | null> {
  const db = getRawDb();
  await ensureTable(db);
  const row = await readRow(db, normalizedRequestId(requestId));
  return row ? snapshot(row) : null;
}

export async function finalizeDirectReadingPreviewJob(
  requestId: string,
  resultStatus: string,
): Promise<void> {
  const db = getRawDb();
  await ensureTable(db);
  const status = resultStatus.trim().toUpperCase().replace(/[^A-Z0-9_-]/g, "_").slice(0, 64) || "UNKNOWN";
  await db.prepare(`UPDATE direct_reading_preview_jobs
    SET state = 'FINALIZED', result_status = ?, updated_at = ?
    WHERE request_id = ? AND state = 'RUNNING'`).bind(
    status,
    new Date().toISOString(),
    normalizedRequestId(requestId),
  ).run();
}

export async function markDirectReadingPreviewJobLost(requestId: string, reason: string): Promise<void> {
  const db = getRawDb();
  await ensureTable(db);
  const status = reason.trim().toUpperCase().replace(/[^A-Z0-9_-]/g, "_").slice(0, 64) || "LOST";
  await db.prepare(`UPDATE direct_reading_preview_jobs
    SET state = 'LOST', result_status = ?, updated_at = ?
    WHERE request_id = ? AND state = 'RUNNING'`).bind(
    status,
    new Date().toISOString(),
    normalizedRequestId(requestId),
  ).run();
}
