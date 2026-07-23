import { getRawDb } from ".";

export const OWNER_PREVIEW_WINDOW_ID = "first-user-beta-v1";
export const DEFAULT_BETA_REQUEST_LIMIT = 12;

type BudgetRow = {
  window_id: string;
  status: string;
  reserved_calls: number;
  reserved_micro_usd: number;
  actual_micro_usd: number;
  last_result_status: string | null;
  created_at: string;
  updated_at: string;
};

export type OwnerPreviewBudgetSnapshot = {
  allowed: boolean;
  isNewRequest?: boolean;
  requestState?: "NEW" | "IN_FLIGHT" | "FINALIZED" | "RATE_LIMITED";
  status: string;
  reservedCalls: number;
  reservedMicroUsd: number;
  actualMicroUsd: number;
  requestLimit: number;
  remainingCalls: number;
};

type RequestRow = {
  result_status: string | null;
  finalized: number;
};

function requestLimit(): number {
  const configured = Number(process.env.ABALO_PREVIEW_MAX_REQUESTS ?? DEFAULT_BETA_REQUEST_LIMIT);
  if (!Number.isInteger(configured) || configured < 1 || configured > 100) {
    return DEFAULT_BETA_REQUEST_LIMIT;
  }
  return configured;
}

async function ensureBudgetRow(db: D1Database): Promise<void> {
  const now = new Date().toISOString();
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS owner_preview_budget (
      window_id text PRIMARY KEY NOT NULL,
      status text DEFAULT 'OPEN' NOT NULL,
      reserved_calls integer DEFAULT 0 NOT NULL,
      reserved_micro_usd integer DEFAULT 0 NOT NULL,
      actual_micro_usd integer DEFAULT 0 NOT NULL,
      last_result_status text,
      created_at text NOT NULL,
      updated_at text NOT NULL
    )`),
    db.prepare(`CREATE TABLE IF NOT EXISTS owner_preview_requests (
      request_id text PRIMARY KEY NOT NULL,
      result_status text,
      finalized integer DEFAULT 0 NOT NULL,
      actual_micro_usd integer DEFAULT 0 NOT NULL,
      created_at text NOT NULL,
      updated_at text NOT NULL
    )`),
    db.prepare(`INSERT OR IGNORE INTO owner_preview_budget (
      window_id, status, reserved_calls, reserved_micro_usd,
      actual_micro_usd, last_result_status, created_at, updated_at
    ) VALUES (?, 'METERING', 0, 0, 0, NULL, ?, ?)`).bind(
      OWNER_PREVIEW_WINDOW_ID,
      now,
      now,
    ),
  ]);
}

function snapshot(row: BudgetRow, allowed: boolean): OwnerPreviewBudgetSnapshot {
  const limit = requestLimit();
  return {
    allowed,
    status: row.reserved_calls >= limit ? "LIMIT_REACHED" : row.status,
    reservedCalls: row.reserved_calls,
    reservedMicroUsd: row.reserved_micro_usd,
    actualMicroUsd: row.actual_micro_usd,
    requestLimit: limit,
    remainingCalls: Math.max(0, limit - row.reserved_calls),
  };
}

async function readBudgetRow(db: D1Database): Promise<BudgetRow> {
  const row = await db.prepare(
    "SELECT * FROM owner_preview_budget WHERE window_id = ?",
  ).bind(OWNER_PREVIEW_WINDOW_ID).first<BudgetRow>();
  if (!row) throw new Error("Owner preview budget row is unavailable.");
  return row;
}

export async function getOwnerPreviewBudgetSnapshot(): Promise<OwnerPreviewBudgetSnapshot> {
  const db = getRawDb();
  await ensureBudgetRow(db);
  const row = await readBudgetRow(db);
  return snapshot(row, row.reserved_calls < requestLimit());
}

async function readRequestRow(db: D1Database, requestId: string): Promise<RequestRow | null> {
  return db.prepare(
    "SELECT result_status, finalized FROM owner_preview_requests WHERE request_id = ?",
  ).bind(requestId).first<RequestRow>();
}

function normalizedRequestId(requestId: string): string {
  const value = requestId.trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(value)) {
    throw new Error("Invalid owner preview request id.");
  }
  return value;
}

export async function reserveOwnerPreviewAttempt(requestId: string): Promise<OwnerPreviewBudgetSnapshot> {
  const db = getRawDb();
  await ensureBudgetRow(db);
  const now = new Date().toISOString();
  const inserted = await db.prepare(`INSERT OR IGNORE INTO owner_preview_requests (
    request_id, result_status, finalized, actual_micro_usd, created_at, updated_at
  ) VALUES (?, NULL, 0, 0, ?, ?)`).bind(
    normalizedRequestId(requestId),
    now,
    now,
  ).run();
  const isNewRequest = Number(inserted.meta?.changes ?? 0) === 1;
  if (!isNewRequest) {
    const existing = await readRequestRow(db, normalizedRequestId(requestId));
    const finalized = Number(existing?.finalized ?? 0) === 1;
    return {
      ...snapshot(await readBudgetRow(db), !finalized),
      isNewRequest: false,
      requestState: finalized ? "FINALIZED" : "IN_FLIGHT",
    };
  }
  const result = await db.prepare(`UPDATE owner_preview_budget
    SET reserved_calls = reserved_calls + 1,
        status = 'METERING',
        updated_at = ?
    WHERE window_id = ? AND reserved_calls < ?`).bind(
    now,
    OWNER_PREVIEW_WINDOW_ID,
    requestLimit(),
  ).run();
  const row = await readBudgetRow(db);
  const allowed = Number(result.meta?.changes ?? 0) === 1;
  if (!allowed) {
    await db.prepare(`UPDATE owner_preview_requests
      SET result_status = 'RATE_LIMITED', finalized = 1, updated_at = ?
      WHERE request_id = ? AND finalized = 0`).bind(
      now,
      normalizedRequestId(requestId),
    ).run();
  }
  return {
    ...snapshot(row, allowed),
    isNewRequest: true,
    requestState: allowed ? "NEW" : "RATE_LIMITED",
  };
}

export async function recordOwnerPreviewResult(
  requestId: string,
  resultStatus: string,
  actualCostUsd: number | null,
): Promise<OwnerPreviewBudgetSnapshot> {
  const db = getRawDb();
  const normalizedStatus = resultStatus.trim().toUpperCase().replace(/[^A-Z0-9_-]/g, "_").slice(0, 64) || "UNKNOWN";
  const actualMicroUsd =
    typeof actualCostUsd === "number" && Number.isFinite(actualCostUsd) && actualCostUsd >= 0
      ? Math.round(actualCostUsd * 1_000_000)
      : 0;
  const finalized = await db.prepare(`UPDATE owner_preview_requests
    SET result_status = ?,
        finalized = 1,
        actual_micro_usd = ?,
        updated_at = ?
    WHERE request_id = ? AND finalized = 0`).bind(
    normalizedStatus,
    actualMicroUsd,
    new Date().toISOString(),
    normalizedRequestId(requestId),
  ).run();
  if (Number(finalized.meta?.changes ?? 0) !== 1) {
    return snapshot(await readBudgetRow(db), false);
  }
  const result = await db.prepare(`UPDATE owner_preview_budget
    SET actual_micro_usd = actual_micro_usd + ?,
        last_result_status = ?,
        updated_at = ?
    WHERE window_id = ?`).bind(
    actualMicroUsd,
    normalizedStatus,
    new Date().toISOString(),
    OWNER_PREVIEW_WINDOW_ID,
  ).run();
  if (Number(result.meta?.changes ?? 0) !== 1) {
    throw new Error("Owner preview budget result was not persisted.");
  }
  return snapshot(await readBudgetRow(db), true);
}
