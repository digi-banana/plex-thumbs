import hashlib
import os
import requests
from plexapi.server import PlexServer
from sqlalchemy.orm import Session
from datetime import datetime
from . import models, schemas

class PlexService:
    def __init__(self, plex_url: str, plex_token: str, plex_data_dir: str, hub_url: str):
        self.plex = PlexServer(plex_url, plex_token)
        self.plex_data_dir = plex_data_dir
        self.hub_url = hub_url

    def calculate_sha256(self, file_path: str) -> str:
        if not os.path.exists(file_path): return "FILE_NOT_FOUND"
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_bif_path(self, part_hash: str) -> str:
        if not part_hash: return None
        return os.path.join(self.plex_data_dir, "Media", "localhost", part_hash[0], f"{part_hash[1:]}.bundle", "Contents", "index-sd.bif")

    def scan_library(self, db: Session, section_name: str):
        section = self.plex.library.section(section_name)
        for item in section.all():
            if item.type == 'show':
                for episode in item.episodes(): self._process_item(db, episode)
            else: self._process_item(db, item)

    def _process_item(self, db: Session, item):
        for media in item.media:
            for part in media.parts:
                db_item = db.query(models.MediaItem).filter(models.MediaItem.plex_rating_key == str(item.ratingKey)).first()
                if not db_item:
                    db_item = models.MediaItem(
                        plex_rating_key=str(item.ratingKey),
                        title=item.title if item.type != 'episode' else f"{item.grandparentTitle} - {item.title}",
                        media_type=item.type,
                        file_path=part.file,
                        plex_hash=part.hash,
                        sync_status="pending"
                    )
                    db.add(db_item)
                    db.commit()
                    db.refresh(db_item)

                bif_path = self.get_bif_path(part.hash)
                has_local_bif = os.path.exists(bif_path) if bif_path else False

                if has_local_bif:
                    # Update DB with BIF info if missing
                    db_bif = db.query(models.BifFile).filter(models.BifFile.media_item_id == db_item.id).first()
                    if not db_bif:
                        bif_hash = self.calculate_sha256(bif_path)
                        db_bif = models.BifFile(media_item_id=db_item.id, file_path=bif_path, bif_hash=bif_hash, bif_type="index-sd.bif")
                        db.add(db_bif)
                        db_item.sync_status = "local_only"
                        db.commit()
                else:
                    db_item.sync_status = "missing_locally"
                    db.commit()

    def get_tmdb_metadata(self, title, year=None, media_type='movie'):
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key: return None, None
        
        search_type = 'movie' if media_type == 'movie' else 'tv'
        url = f"https://api.themoviedb.org/3/search/{search_type}"
        params = {"api_key": api_key, "query": title}
        if year: params["year" if media_type == 'movie' else "first_air_date_year"] = year
        
        try:
            res = requests.get(url, params=params).json()
            results = res.get('results', [])
            if results:
                best_match = results[0]
                summary = best_match.get('overview', 'No summary found on TMDB.')
                poster_path = best_match.get('poster_path')
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                return summary, poster_url
        except Exception as e:
            print(f"TMDB fetch error: {e}")
        return None, None

    def sync_item(self, db: Session, item_id: int):
        item = db.query(models.MediaItem).get(item_id)
        if not item: return

        # Get metadata from Plex first to get title/year for TMDB search
        try:
            plex_item = self.plex.library.metadata(item.plex_rating_key)
            title = plex_item.title if item.media_type != 'episode' else plex_item.grandparentTitle
            year = plex_item.year
            
            # Now fetch from TMDB
            summary, poster_url = self.get_tmdb_metadata(title, year, item.media_type)
            
            # Fallback to Plex if TMDB fails
            if not summary: summary = getattr(plex_item, 'summary', 'No summary available.')
            if not poster_url: poster_url = plex_item.thumbUrl if hasattr(plex_item, 'thumb') else None
        except Exception as e:
            print(f"Metadata fetch error: {e}")
            title, summary, poster_url = item.title, "No metadata available.", None
        
        ghost_email = os.getenv("GHOST_MEMBER_EMAIL")

        try:
            hub_res = requests.get(f"{self.hub_url}/check/{item.plex_hash}").json()
            hub_exists = hub_res.get("exists")
        except: return

        bif_path = self.get_bif_path(item.plex_hash)
        has_local_bif = os.path.exists(bif_path) if bif_path else False

        if has_local_bif and not hub_exists:
            # Upload with Metadata and Contributor ID
            params = {
                "email": ghost_email,
                "title": title, 
                "summary": summary, 
                "poster_url": poster_url
            }
            with open(bif_path, "rb") as f:
                requests.post(f"{self.hub_url}/upload/{item.plex_hash}", params=params, files={"file": f})
            item.sync_status = "synced"
        elif not has_local_bif and hub_exists:
            # Download with Auth
            params = {"email": ghost_email}
            res = requests.get(f"{self.hub_url}/download/{item.plex_hash}", params=params, stream=True)
            if res.status_code == 200:
                os.makedirs(os.path.dirname(bif_path), exist_ok=True)
                with open(bif_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192): f.write(chunk)
                item.sync_status = "synced"
            elif res.status_code == 403:
                print("Access denied: Not a Ghost member")
