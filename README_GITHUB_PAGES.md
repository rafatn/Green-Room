# Green Room V5.5 — GitHub Pages + FastAPI

## 1. GitHub Pages
Upload the contents of this folder to the GitHub Pages repository. `index.html` must be in the published root.

The frontend loads the 129-company catalog from `companies.json` and logo metadata from `static/logos/index.json`.

## 2. FastAPI server
The backend is `api_server.py`.

Local test:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn api_server:app --reload
```

Open `/docs` on the FastAPI server to inspect the API.

## 3. API keys
Put real keys ONLY in the FastAPI server environment:

```env
FINNHUB_API_KEY=your_real_key
ALPHA_VANTAGE_API_KEY=your_real_key
CORS_ORIGINS=https://YOUR-USERNAME.github.io
```

Never put real keys in `index.html`, `config.js`, `companies.json`, or GitHub.

## 4. Connect GitHub Pages to the API
Edit `config.js`:

```js
window.GREEN_ROOM_API_BASE = 'https://YOUR-GREEN-ROOM-API.onrender.com';
```

Use the HTTPS URL of the deployed FastAPI service, without a trailing slash.

## 5. Render
A `render.yaml` and `Procfile` are included. On Render, set:
- `FINNHUB_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `CORS_ORIGINS` to the exact GitHub Pages origin

The frontend never receives the API keys; it receives only API results.
