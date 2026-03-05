# Plex Thumbs

Plex Thumbs is a self-contained client for the Plex BIF Ecosystem. It runs on your Plex Media Server, scans your library for thumbnails (BIF files), and synchronizes them with the central repository at `api.plexthumbs.qzz.io`.

## Features
- **All-in-One Container**: Bundles the React UI and FastAPI backend into a single image.
- **Bi-directional Sync**: 
    - **Upload**: Shares your local BIFs to the central repository.
    - **Download**: Automatically fetches missing BIFs from the repository to your local Plex server.
- **Plex API Integration**: Uses unique Plex hashes to ensure 100% accurate file matching.

## Setup

### Run with Docker (Recommended)
```bash
docker run -d \
  --name plex-thumbs \
  -p 8000:8000 \
  -v "/path/to/Plex Media Server:/plex_data:ro" \
  -e PLEX_URL="http://your-plex-ip:32400" \
  -e PLEX_TOKEN="your_plex_token" \
  -e GHOST_MEMBER_EMAIL="your-ghost-email@example.com" \
  -e HUB_URL="https://api.plexthumbs.qzz.io" \
  -e TMDB_API_KEY="your_tmdb_key" \
  digi-banana/plex-thumbs
```

### Configuration Variables
- `PLEX_DATA_DIR`: Internal path to Plex Media (default: `/plex_data`).
- `HUB_URL`: The central repository API (default: `https://api.plexthumbs.qzz.io`).
- `AUTO_SYNC_HOURS`: How often to run background sync (default: `6`).

## Development
To run locally without Docker:
1. **Frontend**: `npm install && npm start`
2. **Backend**: `pip install -r backend/requirements.txt && uvicorn backend.app.main:app`
