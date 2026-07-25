import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const observations = sqliteTable("observations", {
  id: text("id").primaryKey(),
  ownerKeyHash: text("owner_key_hash").notNull(),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
  question: text("question").notNull(),
  intakeJson: text("intake_json").notNull(),
  numbersJson: text("numbers_json").notNull(),
  resultJson: text("result_json").notNull(),
  actionText: text("action_text").notNull(),
  reviewOn: text("review_on"),
  realityText: text("reality_text").notNull().default(""),
  learningText: text("learning_text").notNull().default(""),
  status: text("status").notNull().default("OPEN"),
}, (table) => [
  index("observations_owner_updated_idx").on(table.ownerKeyHash, table.updatedAt),
]);

export const feedback = sqliteTable("feedback", {
  id: text("id").primaryKey(),
  createdAt: text("created_at").notNull(),
  kind: text("kind").notNull(),
  content: text("content").notNull(),
  contact: text("contact"),
  page: text("page").notNull(),
});

export const ownerPreviewBudget = sqliteTable("owner_preview_budget", {
  windowId: text("window_id").primaryKey(),
  status: text("status").notNull().default("OPEN"),
  reservedCalls: integer("reserved_calls").notNull().default(0),
  reservedMicroUsd: integer("reserved_micro_usd").notNull().default(0),
  actualMicroUsd: integer("actual_micro_usd").notNull().default(0),
  lastResultStatus: text("last_result_status"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const ownerPreviewRequests = sqliteTable("owner_preview_requests", {
  requestId: text("request_id").primaryKey(),
  resultStatus: text("result_status"),
  finalized: integer("finalized", { mode: "boolean" }).notNull().default(false),
  actualMicroUsd: integer("actual_micro_usd").notNull().default(0),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const publicRequestRateLimits = sqliteTable("public_request_rate_limits", {
  requestId: text("request_id").primaryKey(),
  subjectHash: text("subject_hash").notNull(),
  createdAt: text("created_at").notNull(),
}, (table) => [
  index("public_request_rate_limits_subject_created_idx").on(table.subjectHash, table.createdAt),
]);
