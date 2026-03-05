from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BifFileBase(BaseModel):
    file_path: str
    bif_hash: str
    bif_type: str

class BifFileCreate(BifFileBase):
    pass

class BifFile(BifFileBase):
    id: int
    media_item_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class MediaItemBase(BaseModel):
    plex_rating_key: str
    title: str
    media_type: str
    file_path: str
    plex_hash: str

class MediaItemCreate(MediaItemBase):
    pass

class MediaItem(MediaItemBase):
    id: int
    created_at: datetime
    bif_files: List[BifFile] = []

    class Config:
        from_attributes = True
