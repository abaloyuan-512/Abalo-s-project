CREATE TABLE `owner_preview_budget` (
	`window_id` text PRIMARY KEY NOT NULL,
	`status` text DEFAULT 'OPEN' NOT NULL,
	`reserved_calls` integer DEFAULT 0 NOT NULL,
	`reserved_micro_usd` integer DEFAULT 0 NOT NULL,
	`actual_micro_usd` integer DEFAULT 0 NOT NULL,
	`last_result_status` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
