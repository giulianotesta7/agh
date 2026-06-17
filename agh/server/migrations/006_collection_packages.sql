-- Global skill collection package assignments.

CREATE TABLE IF NOT EXISTS collection_packages (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL,
    package_id TEXT NOT NULL,
    version_ref TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (collection_id, package_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
    FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
);
