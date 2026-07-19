import { drizzle } from "drizzle-orm/d1";
import * as schema from "./schema";

let runtimeDb: D1Database | null = null;
let schemaReady: Promise<void> | null = null;

export function setRuntimeDb(db: D1Database | undefined) {
  const next = db ?? null;
  if (next !== runtimeDb) schemaReady = null;
  runtimeDb = next;
}

export async function ensureProductSchema() {
  if (!runtimeDb) throw new Error("Cloudflare D1 binding `DB` is unavailable.");
  schemaReady ??= runtimeDb.batch([
    runtimeDb.prepare(`CREATE TABLE IF NOT EXISTS observations (
      id text PRIMARY KEY NOT NULL,
      owner_key_hash text NOT NULL,
      created_at text NOT NULL,
      updated_at text NOT NULL,
      question text NOT NULL,
      intake_json text NOT NULL,
      numbers_json text NOT NULL,
      result_json text NOT NULL,
      action_text text NOT NULL,
      review_on text,
      reality_text text DEFAULT '' NOT NULL,
      learning_text text DEFAULT '' NOT NULL,
      status text DEFAULT 'OPEN' NOT NULL
    )`),
    runtimeDb.prepare("CREATE INDEX IF NOT EXISTS observations_owner_updated_idx ON observations (owner_key_hash, updated_at)"),
    runtimeDb.prepare(`CREATE TABLE IF NOT EXISTS feedback (
      id text PRIMARY KEY NOT NULL,
      created_at text NOT NULL,
      kind text NOT NULL,
      content text NOT NULL,
      contact text,
      page text NOT NULL
    )`),
  ]).then(() => undefined).catch((error) => { schemaReady = null; throw error; });
  await schemaReady;
}

export function getDb() {
  if (!runtimeDb) {
    throw new Error(
      "Cloudflare D1 binding `DB` is unavailable. Set the `d1` field in .openai/hosting.json to `DB` or let your control plane inject the real binding values before using the database."
    );
  }

  return drizzle(runtimeDb, { schema });
}
