CREATE TABLE IF NOT EXISTS matters (
    matter_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    case_number TEXT,
    court TEXT,
    jurisdiction TEXT,
    stage TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, matter_id)
);

CREATE INDEX IF NOT EXISTS idx_matters_user_archived_updated
ON matters (user_id, is_archived, updated_at DESC);

CREATE TABLE IF NOT EXISTS matter_parties (
    party_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    name TEXT NOT NULL,
    party_role TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_parties_owner
ON matter_parties (user_id, matter_id, is_archived, created_at);

CREATE TABLE IF NOT EXISTS matter_hearings (
    hearing_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    title TEXT NOT NULL,
    hearing_at TIMESTAMPTZ,
    court TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',
    notes TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_hearings_owner_date
ON matter_hearings (user_id, matter_id, is_archived, hearing_at);

CREATE TABLE IF NOT EXISTS matter_tasks (
    task_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    due_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'normal',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_tasks_owner_status_due
ON matter_tasks (user_id, matter_id, is_archived, status, due_at);

CREATE TABLE IF NOT EXISTS matter_notes (
    note_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_notes_owner_created
ON matter_notes (user_id, matter_id, is_archived, created_at DESC);

CREATE TABLE IF NOT EXISTS matter_events (
    event_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    event_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_type TEXT,
    source_id UUID,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_events_owner_date
ON matter_events (user_id, matter_id, is_archived, event_at DESC);

CREATE TABLE IF NOT EXISTS matter_documents (
    document_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    title TEXT NOT NULL,
    file_name TEXT,
    storage_path TEXT,
    mime_type TEXT,
    size_bytes BIGINT,
    sha256 TEXT,
    extraction_status TEXT NOT NULL DEFAULT 'pending',
    extracted_text TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_documents_owner_created
ON matter_documents (user_id, matter_id, is_archived, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_matter_documents_sha256
ON matter_documents (user_id, matter_id, sha256)
WHERE sha256 IS NOT NULL;

CREATE TABLE IF NOT EXISTS matter_research (
    research_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    title TEXT NOT NULL,
    query TEXT NOT NULL,
    content TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_status TEXT NOT NULL DEFAULT 'pending',
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_research_owner_updated
ON matter_research (user_id, matter_id, is_archived, updated_at DESC);

CREATE TABLE IF NOT EXISTS matter_drafts (
    draft_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, matter_id, draft_id),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_drafts_owner_updated
ON matter_drafts (user_id, matter_id, is_archived, updated_at DESC);

CREATE TABLE IF NOT EXISTS draft_versions (
    version_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    draft_id UUID NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    content TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by UUID NOT NULL REFERENCES app_users(user_id),
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, matter_id, draft_id, version_number),
    FOREIGN KEY (user_id, matter_id, draft_id)
        REFERENCES matter_drafts(user_id, matter_id, draft_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_draft_versions_owner_version
ON draft_versions (user_id, matter_id, draft_id, version_number DESC);

CREATE TABLE IF NOT EXISTS agent_runs (
    agent_run_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    command TEXT NOT NULL,
    input_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'created',
    context_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_text TEXT,
    error_text TEXT,
    model_id TEXT,
    prompt_version TEXT,
    token_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, matter_id, agent_run_id),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_owner_status
ON agent_runs (user_id, matter_id, is_archived, status, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_tool_calls (
    tool_call_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    agent_run_id UUID NOT NULL,
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'started',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB,
    error_text TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id, agent_run_id)
        REFERENCES agent_runs(user_id, matter_id, agent_run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_owner_run
ON agent_tool_calls (user_id, matter_id, agent_run_id, is_archived, created_at);

CREATE TABLE IF NOT EXISTS agent_feedback (
    feedback_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    agent_run_id UUID,
    research_id UUID,
    draft_id UUID,
    feedback_type TEXT NOT NULL,
    rating INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id, matter_id)
        REFERENCES matters(user_id, matter_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_run_id)
        REFERENCES agent_runs(agent_run_id) ON DELETE SET NULL,
    FOREIGN KEY (research_id)
        REFERENCES matter_research(research_id) ON DELETE SET NULL,
    FOREIGN KEY (draft_id)
        REFERENCES matter_drafts(draft_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_feedback_owner_created
ON agent_feedback (user_id, matter_id, is_archived, created_at DESC);

CREATE OR REPLACE FUNCTION set_v1_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_matters_updated_at ON matters;
CREATE TRIGGER trg_matters_updated_at
BEFORE UPDATE ON matters
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_parties_updated_at ON matter_parties;
CREATE TRIGGER trg_matter_parties_updated_at
BEFORE UPDATE ON matter_parties
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_hearings_updated_at ON matter_hearings;
CREATE TRIGGER trg_matter_hearings_updated_at
BEFORE UPDATE ON matter_hearings
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_tasks_updated_at ON matter_tasks;
CREATE TRIGGER trg_matter_tasks_updated_at
BEFORE UPDATE ON matter_tasks
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_notes_updated_at ON matter_notes;
CREATE TRIGGER trg_matter_notes_updated_at
BEFORE UPDATE ON matter_notes
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_events_updated_at ON matter_events;
CREATE TRIGGER trg_matter_events_updated_at
BEFORE UPDATE ON matter_events
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_documents_updated_at ON matter_documents;
CREATE TRIGGER trg_matter_documents_updated_at
BEFORE UPDATE ON matter_documents
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_research_updated_at ON matter_research;
CREATE TRIGGER trg_matter_research_updated_at
BEFORE UPDATE ON matter_research
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_matter_drafts_updated_at ON matter_drafts;
CREATE TRIGGER trg_matter_drafts_updated_at
BEFORE UPDATE ON matter_drafts
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_agent_runs_updated_at ON agent_runs;
CREATE TRIGGER trg_agent_runs_updated_at
BEFORE UPDATE ON agent_runs
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_agent_tool_calls_updated_at ON agent_tool_calls;
CREATE TRIGGER trg_agent_tool_calls_updated_at
BEFORE UPDATE ON agent_tool_calls
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

DROP TRIGGER IF EXISTS trg_agent_feedback_updated_at ON agent_feedback;
CREATE TRIGGER trg_agent_feedback_updated_at
BEFORE UPDATE ON agent_feedback
FOR EACH ROW EXECUTE FUNCTION set_v1_updated_at();

CREATE OR REPLACE FUNCTION prevent_v1_draft_version_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'draft_versions are immutable';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_draft_versions_immutable ON draft_versions;
CREATE TRIGGER trg_draft_versions_immutable
BEFORE UPDATE OR DELETE ON draft_versions
FOR EACH ROW EXECUTE FUNCTION prevent_v1_draft_version_mutation();
