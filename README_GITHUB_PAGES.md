# Green Room — GitHub Pages

This package is prepared for GitHub Pages.

## Upload
1. Create a public GitHub repository.
2. Upload the contents of this folder so `index.html` is at the repository root.
3. Settings → Pages → Deploy from a branch → `main` → `/ (root)`.

## Included
- 129-company local catalog.
- Local logo catalog plus CDN fallback for the existing Simple Icons brand assets.
- Company details modal: click any company to open its summary.
- Hebrew, English, Arabic and Russian summaries.
- Static-site fallback for the API-dependent market features.

## Important
GitHub Pages can host the static interface, company catalog and summaries, but it does not run the FastAPI/Python backend. Live quotes, historical data and optimization API endpoints therefore require the original FastAPI server deployment.
