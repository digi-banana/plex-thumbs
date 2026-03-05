from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True, index=True)
    plex_rating_key = Column(String, unique=True, index=True)
    title = Column(String)
    media_type = Column(String) # 'movie' or 'episode'
    file_path = Column(String)
    plex_hash = Column(String, index=True)
    sync_status = Column(String, default="pending") # 'pending', 'synced', 'missing_locally', 'missing_remotely'
    last_synced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bif_files = relationship("BifFile", back_populates="media_item")

class BifFile(Base):
    __tablename__ = "bif_files"

    id = Column(Integer, primary_key=True, index=True)
    media_item_id = Column(Integer, ForeignKey("media_items.id"))
    file_path = Column(String)
    bif_hash = Column(String) # SHA-256 for the BIF file
    bif_type = Column(String) # 'index-sd.bif'
    created_at = Column(DateTime, default=datetime.utcnow)

    media_item = relationship("MediaItem", back_populates="bif_files")
