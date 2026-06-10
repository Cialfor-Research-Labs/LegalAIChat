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

- Chat RAG is local-first and uses bundled statute data plus a curated case-law corpus.
- Retrieval is deterministic and in-memory; it does not add a second LLM call.
- Sensitive runtime values must stay in `tllac/.env` and should never be committed.
