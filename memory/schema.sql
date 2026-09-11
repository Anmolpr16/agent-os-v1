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

CREATE TABLE IF NOT EXISTS governance_proposals (
    proposal_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    proposal_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS governance_decisions (
    decision_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    status TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (proposal_id) REFERENCES governance_proposals(proposal_id)
);

CREATE INDEX IF NOT EXISTS idx_governance_proposals_task
    ON governance_proposals(task_id);

CREATE INDEX IF NOT EXISTS idx_governance_proposals_status
    ON governance_proposals(status);

CREATE INDEX IF NOT EXISTS idx_governance_decisions_proposal
    ON governance_decisions(proposal_id);

CREATE INDEX IF NOT EXISTS idx_governance_decisions_timestamp
    ON governance_decisions(timestamp);
