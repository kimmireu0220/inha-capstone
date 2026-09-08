CREATE TABLE `submissions` (
	`id` text PRIMARY KEY NOT NULL,
	`schema` text NOT NULL,
	`received_at` text NOT NULL,
	`age` text NOT NULL,
	`exposure` text NOT NULL,
	`payload` text NOT NULL,
	`payload_hash` text NOT NULL
);
