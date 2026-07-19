import { index, sqliteTable, text } from "drizzle-orm/sqlite-core";

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
