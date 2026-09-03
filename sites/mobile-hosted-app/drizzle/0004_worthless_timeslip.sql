CREATE TABLE `direct_reading_preview_jobs` (
	`request_id` text PRIMARY KEY NOT NULL,
	`payload_sha256` text NOT NULL,
	`prompt_version` text NOT NULL,
	`state` text DEFAULT 'RUNNING' NOT NULL,
	`result_status` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
