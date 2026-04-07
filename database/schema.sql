-- database/schema.sql
-- Run once against your AlloyDB / PostgreSQL instance to initialise the schema.

-- ── Tasks table ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id          SERIAL PRIMARY KEY,
    task        TEXT        NOT NULL,
    due_date    DATE,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_progress', 'done')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Notes table ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notes (
    id          SERIAL PRIMARY KEY,
    content     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);
CREATE INDEX IF NOT EXISTS idx_notes_created  ON notes (created_at DESC);