from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
from dotenv import load_dotenv

from . import models, schemas, database, plex_service

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

load_dotenv()

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Plex BIF Ecosystem Client")

# ... (middleware and config)

def auto_sync_task():
    print(f"[{datetime.now()}] Starting scheduled auto-sync...")
    db = next(database.get_db())
    plex = get_plex_service()
    items = db.query(models.MediaItem).filter(models.MediaItem.sync_status != "synced").all()
    for item in items:
        try: plex.sync_item(db, item.id)
        except Exception as e: print(f"Sync error for {item.title}: {e}")
    db.close()

@app.on_event("startup")
def start_scheduler():
    interval_hours = int(os.getenv("AUTO_SYNC_HOURS", "6"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_sync_task, 'interval', hours=interval_hours)
    scheduler.start()
    print(f"Scheduler started: running every {interval_hours} hours.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
PLEX_DATA_DIR = os.getenv("PLEX_DATA_DIR")
HUB_URL = os.getenv("HUB_URL", "http://hub:8001")

def get_plex_service():
    if not PLEX_TOKEN or not PLEX_DATA_DIR:
        raise HTTPException(status_code=500, detail="Plex configuration missing")
    return plex_service.PlexService(PLEX_URL, PLEX_TOKEN, PLEX_DATA_DIR, HUB_URL)

@app.get("/media", response_model=List[schemas.MediaItem])
def get_media_items(db: Session = Depends(database.get_db)):
    return db.query(models.MediaItem).all()

@app.post("/scan")
def start_scan(section_name: str, background_tasks: BackgroundTasks, 
               db: Session = Depends(database.get_db),
               plex: plex_service.PlexService = Depends(get_plex_service)):
    background_tasks.add_task(plex.scan_library, db, section_name)
    return {"message": f"Scan started for {section_name}"}

@app.post("/sync/{item_id}")
def sync_item(item_id: int, background_tasks: BackgroundTasks,
              db: Session = Depends(database.get_db),
              plex: plex_service.PlexService = Depends(get_plex_service)):
    background_tasks.add_task(plex.sync_item, db, item_id)
    return {"message": "Sync started"}

@app.post("/sync-all")
def sync_all(background_tasks: BackgroundTasks,
             db: Session = Depends(database.get_db),
             plex: plex_service.PlexService = Depends(get_plex_service)):
    items = db.query(models.MediaItem).all()
    for item in items:
        background_tasks.add_task(plex.sync_item, db, item.id)
    return {"message": f"Syncing {len(items)} items"}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Static file paths
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
build_path = os.path.join(base_dir, "build")
static_path = os.path.join(build_path, "static")

# Serve React static assets
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    # If the path exists as a file in build (like favicon.ico), serve it
    file_path = os.path.join(build_path, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Otherwise, serve index.html for React Router to handle
    index_path = os.path.join(build_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {"error": "Not Found"}
