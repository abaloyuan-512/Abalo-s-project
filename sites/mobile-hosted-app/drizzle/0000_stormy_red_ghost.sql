CREATE TABLE `feedback` (
	`id` text PRIMARY KEY NOT NULL,
	`created_at` text NOT NULL,
	`kind` text NOT NULL,
	`content` text NOT NULL,
	`contact` text,
	`page` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `observations` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_key_hash` text NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`question` text NOT NULL,
	`intake_json` text NOT NULL,
	`numbers_json` text NOT NULL,
	`result_json` text NOT NULL,
	`action_text` text NOT NULL,
	`review_on` text,
	`reality_text` text DEFAULT '' NOT NULL,
	`learning_text` text DEFAULT '' NOT NULL,
	`status` text DEFAULT 'OPEN' NOT NULL
);
--> statement-breakpoint
CREATE INDEX `observations_owner_updated_idx` ON `observations` (`owner_key_hash`,`updated_at`);