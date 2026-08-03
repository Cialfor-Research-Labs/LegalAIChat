# TLLAC - Trained Legal AI Chat Backend

Isolated FastAPI backend for the experimental legal chat UI on port `9001`.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Configure `tllac/.env` using `tllac/.env.example` as the template. Keep real credentials only in `tllac/.env`.

```env
DATABASE_URL=postgresql://user:password@host:5432/legalaichat
APP_SECRET_KEY=replace-with-a-long-random-secret
CHAT_ENCRYPTION_KEY=replace-with-a-fernet-key
AWS_REGION=your-aws-region
MODEL_ID=your-bedrock-model-id
LEGAL_RAG_ENABLED=true
LEGAL_RAG_MAX_STATUTES=3
LEGAL_RAG_MAX_CASES=2
LEGAL_RAG_MAX_CHARS=1800
LEGAL_RAG_MIN_RESPONSE_CONFIDENCE=0.42
LEGAL_RAG_ALLOW_ONLINE_CONTEXT=false
LEGAL_RAG_CORPUS_ROOT=..
LEGAL_RAG_INDEX_PATH=app/data/legal_corpus.sqlite3
MATTER_DOCUMENT_UPLOAD_ROOT=uploads
ONLINE_LEGAL_RESEARCH_ENABLED=false
```

Generate the encryption key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

4. Run the backend with `uvicorn app.main:app --reload --port 9001`.

## Auth and Chat APIs

- `POST /auth/register` creates a user and returns a bearer token.
- `POST /auth/login` authenticates an existing user.
- `GET /auth/me` returns the current user for a bearer token.
- `POST /chat` sends a chat message for the authenticated user.
- `GET /chat/sessions` lists the user's saved sessions.
- `GET /chat/sessions/{session_id}` returns one decrypted session.

## Matter Document APIs

- `POST /matter-documents/upload` uploads a PDF, DOCX, or TXT file for an authenticated user and matter.
- `GET /matter-documents?matter_id=...` lists documents for a matter.
- `GET /matter-documents/{document_id}` returns document metadata.
- `GET /matter-documents/{document_id}/download` downloads the stored file.
- `GET /matter-documents/{document_id}/view` streams the stored file inline.
- `DELETE /matter-documents/{document_id}` marks a document deleted and removes the local file.
- `POST /matter-documents/{document_id}/archive` marks a document archived.
- `GET /matter-documents/search?matter_id=...&query=...` searches matter documents.

Example chat request:

```json
{
  "query": "What is adverse possession in India?",
  "session_id": null
}
```

## Storage Model

- Users, chat sessions, and encrypted messages are stored in Postgres.
- Chat message bodies are encrypted before persistence.
- Session titles update from the first user prompt and are shown in the sidebar.
- Matter document metadata and extracted chunks are stored in Postgres.
- Uploaded files are saved locally under `tllac/uploads/user_<id>/matter_<id>/`.

## Frontend Notes

The UI now expects login and registration before chat access. It uses the same backend base URL for:

- `/auth/register`
- `/auth/login`
- `/auth/me`
- `/chat`
- `/chat/sessions`

## Health

- Docs: `http://localhost:9001/docs`
- Health check: `http://localhost:9001/`

## Chat Retrieval

- Chat RAG is local-first and uses bundled statute data, a curated case-law corpus, and an optional indexed JSON corpus.
- Retrieval is deterministic and local; the compact curated data stays in memory while the large corpus is queried from its generated index. It does not add a second LLM call.
- Sensitive runtime values must stay in `tllac/.env` and should never be committed.

### Building the JSON corpus index

The raw `json_judgements`, `json_judgements_files`, and `json_law_files` directories are intentionally not committed because they total several gigabytes. Place them under `LEGAL_RAG_CORPUS_ROOT`, then run this from the `tllac` directory:

```bash
python -m app.scripts.build_legal_rag_index
```

Use `--corpus-root` or `--output` to override the configured locations. The builder streams each JSON array, skips invalid records with warnings, deduplicates by `chunk_id`, and atomically replaces the generated SQLite index only after a successful build. Re-run it whenever the source corpus changes.

The application never builds the index during startup. If the index is missing or incompatible, chat continues using the bundled curated corpus and logs a warning. Request-time retrieval reads only the generated index and never scans the raw JSON directories.

### Evaluating retrieval quality

Run the built-in benchmark script to inspect retrieval precision, recall, groundedness, citation accuracy, hallucination rate, and response relevance:

```bash
python -m app.scripts.evaluate_legal_rag
```

Pass `--responses path/to/responses.json` if you want to score stored model answers against the benchmark.
