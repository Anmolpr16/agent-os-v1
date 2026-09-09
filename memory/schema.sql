PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uri TEXT,
    title TEXT,
    content_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL
        CHECK (kind IN (
            'semantic',
            'episodic',
            'procedural',
            'working'
        )),
    content TEXT NOT NULL,
    source_id INTEGER REFERENCES sources(id),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL
        REFERENCES entities(id),
    relation TEXT NOT NULL,
    target_entity_id INTEGER NOT NULL
        REFERENCES entities(id),
    metadata_json TEXT NOT NULL DEFAULT '{}',

    UNIQUE (
        source_entity_id,
        relation,
        target_entity_id
    )
);

CREATE TABLE IF NOT EXISTS task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    state TEXT NOT NULL,
    result_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_kind
    ON memory_items(kind);

CREATE INDEX IF NOT EXISTS idx_memory_created
    ON memory_items(created_at);

CREATE INDEX IF NOT EXISTS idx_relationship_source
    ON relationships(source_entity_id);

CREATE INDEX IF NOT EXISTS idx_relationship_target
    ON relationships(target_entity_id);
