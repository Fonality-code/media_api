from datetime import datetime
from typing import Optional, List
from enum import Enum

from beanie import Document, Indexed
from pydantic import Field


class FileStatus(str, Enum):
    ACTIVE = "active"
    FLAGGED = "flagged"
    DELETED = "deleted"
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"


class GridFSFile(Document):
    filename: str
    content_type: str
    upload_date: datetime = Field(default_factory=datetime.now)
    file_id: str
    owner_id: Optional[str] = Field(default=None, description="ID of the user who uploaded the file")
    status: FileStatus = Field(default=FileStatus.ACTIVE, description="Status of the file")
    file_size: Optional[int] = Field(default=None, description="Size of the file in bytes")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing files")
    description: Optional[str] = Field(default=None, description="Optional description of the file")
    metadata: Optional[dict] = Field(default_factory=dict)

    class Settings:
        name = "gridfs_files"
        indexes = [
            "owner_id",
            "status",
            "content_type",
            "upload_date",
            [("owner_id", 1), ("status", 1)],  # Compound index
            [("content_type", 1), ("status", 1)],  # Compound index
        ]
