import { getRawDb } from ".";

export const OWNER_PREVIEW_WINDOW_ID = "owner-preview-v1-initial-two-calls";
export const OWNER_PREVIEW_MAX_CALLS = 2;
export const OWNER_PREVIEW_RESERVATION_MICRO_USD = 500_000;
export const OWNER_PREVIEW_TOTAL_MICRO_USD = 1_000_000;

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
  status: string;
  reservedCalls: number;
  remainingCalls: number;
  reservedMicroUsd: number;
  actualMicroUsd: number;
};

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
    db.prepare(`INSERT OR IGNORE INTO owner_preview_budget (
      window_id, status, reserved_calls, reserved_micro_usd,
      actual_micro_usd, last_result_status, created_at, updated_at
    ) VALUES (?, 'OPEN', 0, 0, 0, NULL, ?, ?)`).bind(
      OWNER_PREVIEW_WINDOW_ID,
      now,
      now,
    ),
  ]);
}

function snapshot(row: BudgetRow, allowed: boolean): OwnerPreviewBudgetSnapshot {
  return {
    allowed,
    status: row.status,
    reservedCalls: row.reserved_calls,
    remainingCalls: Math.max(0, OWNER_PREVIEW_MAX_CALLS - row.reserved_calls),
    reservedMicroUsd: row.reserved_micro_usd,
    actualMicroUsd: row.actual_micro_usd,
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
  return snapshot(await readBudgetRow(db), false);
}

export async function reserveOwnerPreviewAttempt(): Promise<OwnerPreviewBudgetSnapshot> {
  const db = getRawDb();
  await ensureBudgetRow(db);
  const now = new Date().toISOString();
  const result = await db.prepare(`UPDATE owner_preview_budget
    SET reserved_calls = reserved_calls + 1,
        reserved_micro_usd = reserved_micro_usd + ?,
        status = CASE
          WHEN reserved_calls + 1 >= ? THEN 'EXHAUSTED'
          ELSE status
        END,
        updated_at = ?
    WHERE window_id = ?
      AND status = 'OPEN'
      AND reserved_calls < ?
      AND reserved_micro_usd + ? <= ?`).bind(
    OWNER_PREVIEW_RESERVATION_MICRO_USD,
    OWNER_PREVIEW_MAX_CALLS,
    now,
    OWNER_PREVIEW_WINDOW_ID,
    OWNER_PREVIEW_MAX_CALLS,
    OWNER_PREVIEW_RESERVATION_MICRO_USD,
    OWNER_PREVIEW_TOTAL_MICRO_USD,
  ).run();
  const row = await readBudgetRow(db);
  return snapshot(row, Number(result.meta?.changes ?? 0) === 1);
}

export async function recordOwnerPreviewResult(
  resultStatus: string,
  actualCostUsd: number | null,
): Promise<void> {
  const db = getRawDb();
  const normalizedStatus = resultStatus.trim().toUpperCase().replace(/[^A-Z0-9_-]/g, "_").slice(0, 64) || "UNKNOWN";
  const actualMicroUsd =
    typeof actualCostUsd === "number" && Number.isFinite(actualCostUsd) && actualCostUsd >= 0
      ? Math.round(actualCostUsd * 1_000_000)
      : 0;
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
}
