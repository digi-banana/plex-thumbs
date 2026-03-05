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

# ... after all other routes like @app.get("/media") etc ...

# Mount React static files
# This MUST be last to not override other routes
build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "build"))
if os.path.exists(build_path):
    app.mount("/", StaticFiles(directory=build_path, html=True), name="static")
else:
    print(f"Warning: Build directory {build_path} not found.")
