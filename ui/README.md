# Experimental Chat UI

This frontend now opens directly into the experimental legal chat.

There is:
- no login
- no admin page
- no generator/analyzer/predictor shell
- no older main app flow

## Run locally

1. Start the `tllac` backend:

```bash
cd tllac
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 9001
```

Windows PowerShell:

```powershell
cd tllac
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 9001
```

2. Start the frontend:

```bash
cd ui
npm install
npm run dev
```

3. Open the chat page directly:

```text
http://localhost:3000
```

## Optional frontend env

If the browser should call a specific backend directly, set:

```env
VITE_TLLAC_API_URL=http://localhost:9001/chat
```

For LAN testing, replace `localhost` with the server IP.
