import { sqliteTable, text } from 'drizzle-orm/sqlite-core';
export const submissions = sqliteTable('submissions', {
  id: text('id').primaryKey(),
  schema: text('schema').notNull(),
  receivedAt: text('received_at').notNull(),
  age: text('age').notNull(),
  exposure: text('exposure').notNull(),
  payload: text('payload').notNull(),
  payloadHash: text('payload_hash').notNull(),
});
