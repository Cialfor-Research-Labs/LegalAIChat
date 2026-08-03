# Vidhi AI V1 Beta skeleton

This folder is the standalone frontend for the V1.0 Beta architecture. It is intentionally separate from the current `ui` application and connects to the shared TLLAC backend through `VITE_V1_API_BASE`.

## Run locally

```powershell
npm install
npm run dev
```

The skeleton runs at `http://localhost:3001`. The current Vidhi AI launcher uses this address by default. Set `VITE_V1_BETA_URL` for a different standalone Beta URL.

## Current capabilities

- Direct login and launch-token authentication
- Matter listing, selection, creation, and overview data
- Matter timeline, tasks, documents, research, and draft summaries
- Matter-bound Case Agent commands

The global Dashboard, Documents hub, Review queue, Team, search, notifications, and source-detail interactions remain planned screens.
