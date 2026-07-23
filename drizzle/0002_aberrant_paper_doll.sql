CREATE TABLE `owner_preview_requests` (
	`request_id` text PRIMARY KEY NOT NULL,
	`result_status` text,
	`finalized` integer DEFAULT false NOT NULL,
	`actual_micro_usd` integer DEFAULT 0 NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
