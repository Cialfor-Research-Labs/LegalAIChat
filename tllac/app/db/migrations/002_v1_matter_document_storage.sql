ALTER TABLE matter_documents
ADD COLUMN IF NOT EXISTS original_filename TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS file_extension TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS upload_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'deleted', 'archived'));

UPDATE matter_documents
SET original_filename = COALESCE(NULLIF(original_filename, ''), file_name, title),
    file_extension = COALESCE(
        NULLIF(file_extension, ''),
        LOWER(SUBSTRING(COALESCE(file_name, '') FROM '\.[^.]+$')),
        ''
    ),
    upload_timestamp = COALESCE(upload_timestamp, created_at),
    status = CASE
        WHEN is_archived THEN 'archived'
        ELSE status
    END;

CREATE UNIQUE INDEX IF NOT EXISTS uq_matter_documents_owner_document
ON matter_documents (user_id, matter_id, document_id);

CREATE INDEX IF NOT EXISTS idx_matter_documents_user_matter_status
ON matter_documents (user_id, matter_id, status, upload_timestamp DESC);

CREATE TABLE IF NOT EXISTS matter_document_chunks (
    chunk_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    user_id UUID NOT NULL,
    matter_id UUID NOT NULL,
    page_number INTEGER,
    paragraph_number INTEGER,
    chunk_position INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    FOREIGN KEY (user_id, matter_id, document_id)
        REFERENCES matter_documents(user_id, matter_id, document_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matter_document_chunks_document_position
ON matter_document_chunks (user_id, matter_id, document_id, chunk_position ASC);

CREATE INDEX IF NOT EXISTS idx_matter_document_chunks_search
ON matter_document_chunks USING GIN (to_tsvector('simple', chunk_text));
