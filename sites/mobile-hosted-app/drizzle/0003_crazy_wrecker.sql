CREATE TABLE `public_request_rate_limits` (
	`request_id` text PRIMARY KEY NOT NULL,
	`subject_hash` text NOT NULL,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `public_request_rate_limits_subject_created_idx` ON `public_request_rate_limits` (`subject_hash`,`created_at`);