# Vidhi AI V1 Beta skeleton

This folder is a standalone frontend shell for the V1.0 Beta architecture. It is intentionally separate from the current `ui` application and contains no API calls, shared sessions, production data access, or write actions.

## Run locally

```powershell
npm install
npm run dev
```

The skeleton runs at `http://localhost:3001`. The current Vidhi AI launcher uses this address by default. Set `VITE_V1_BETA_URL` for a different standalone Beta URL.

## Current boundaries

- Static matter workspace
- Static Case Agent panel and planned command list
- Static source viewer and citation-gate indicators
- Disabled controls throughout
- No authentication exchange, matter persistence, retrieval, model, document, or audit integration
