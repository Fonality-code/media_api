import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from urllib.parse import quote

from bson import ObjectId
from fastapi import (FastAPI, File, HTTPException, UploadFile,
                     Request, Query, Form)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.database import gridfs_bucket, init_db
from app.models.file import GridFSFile, FileStatus


# Pydantic models for request/response
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    status: str
    owner_id: Optional[str] = None


class FileListResponse(BaseModel):
    id: str
    filename: str
    content_type: Optional[str]
    upload_date: Any
    file_size: Optional[int]
    status: FileStatus
    owner_id: Optional[str]
    tags: List[str]
    description: Optional[str]


class FileUpdateRequest(BaseModel):
    status: Optional[FileStatus] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context for startup and shutdown tasks"""
    # Startup code
    await init_db()
    yield
    # Shutdown code (if needed)
    # e.g., closing database connections


app = FastAPI(title="GridFSFile File Storage API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    owner_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    description: Optional[str] = Form(None)
) -> FileUploadResponse:
    """Upload a new file (image or video) to GridFS storage."""
    if not file.content_type or not file.content_type.startswith(("image/", "video/")):
        raise HTTPException(400, "Only images and videos are allowed")

    content_type = file.content_type
    filename = file.filename or "unnamed_file"

    # Read file content to get size
    file_content = await file.read()
    file_size = len(file_content)

    # Reset file pointer
    await file.seek(0)

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Upload to GridFS
    file_id = await gridfs_bucket.upload_from_stream(
        filename,
        file.file,
        metadata={
            "content_type": content_type,
            "original_name": filename,
            "owner_id": owner_id,
            "file_size": file_size
        },
    )

    # Save metadata in MongoDB collection
    gridfs_file = GridFSFile(
        filename=filename,
        content_type=content_type,
        file_id=str(file_id),
        owner_id=owner_id,
        status=FileStatus.ACTIVE,
        file_size=file_size,
        tags=tag_list,
        description=description,
        metadata={"uploaded_by": "api", "source": "upload_endpoint"},
    )

    await gridfs_file.insert()

    return FileUploadResponse(
        file_id=str(file_id),
        filename=filename,
        file_size=file_size,
        status=gridfs_file.status.value,
        owner_id=owner_id
    )


@app.get("/files/{file_id}")
async def get_file(file_id: str, request: Request):
    if not ObjectId.is_valid(file_id):
        raise HTTPException(400, "Invalid file ID")

    oid = ObjectId(file_id)

    # Use find_one to get a single document, or iterate through the cursor
    cursor = gridfs_bucket.find({"_id": oid})
    file_doc = None
    async for doc in cursor:
        file_doc = doc
        break

    if not file_doc:
        raise HTTPException(404, "File Not Found in GridFS")

    filename = file_doc.filename or "file"
    content_type = (
        file_doc.metadata.get("content_type", "video/mp4")
        if file_doc.metadata
        else "video/mp4"
    )
    file_size = file_doc.length

    try:
        grid_out = await asyncio.wait_for(
            gridfs_bucket.open_download_stream(oid), timeout=30.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Timeout File too large or server busy")
    except Exception as e:
        raise HTTPException(400, f"Stream error: {str(e)}")

    async def stream_file():
        try:
            while True:
                chunk = await grid_out.readchunk()
                if not chunk:
                    break
                yield chunk

                if await request.is_disconnected():
                    print("Client Disconnected during download")
                    break
        except Exception as e:
            print(f"Stream error {e}")
        finally:
            grid_out.close()

    # Properly encode filename for Content-Disposition header
    # Use RFC 5987 encoding for Unicode filenames
    try:
        # Try ASCII first
        safe_filename = filename.encode('ascii').decode('ascii')
        content_disposition = f"attachment; filename={safe_filename}"
    except UnicodeEncodeError:
        # Use RFC 5987 encoding for non-ASCII characters
        encoded_filename = quote(filename.encode('utf-8'))
        content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}"

    headers = {
        "Content-Disposition": content_disposition,
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Cache-Control": "public, max-age=3600",
    }

    return StreamingResponse(stream_file(), media_type=content_type, headers=headers)


@app.get("/files/{file_id}/info", response_model=FileListResponse)
async def get_file_info(file_id: str):
    """Get file metadata without downloading the file."""
    if not ObjectId.is_valid(file_id):
        raise HTTPException(400, "Invalid file ID")

    # Find file metadata in our collection
    file_doc = await GridFSFile.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "File not found")

    return FileListResponse(
        id=str(file_doc.id),
        filename=file_doc.filename,
        content_type=file_doc.content_type,
        upload_date=file_doc.upload_date,
        file_size=file_doc.file_size,
        status=file_doc.status,
        owner_id=file_doc.owner_id,
        tags=file_doc.tags,
        description=file_doc.description
    )


@app.put("/files/{file_id}", response_model=FileListResponse)
async def update_file(file_id: str, update_data: FileUpdateRequest):
    """Update file metadata (status, tags, description)."""
    if not ObjectId.is_valid(file_id):
        raise HTTPException(400, "Invalid file ID")

    # Find the file
    file_doc = await GridFSFile.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "File not found")

    # Update only provided fields
    update_dict = {}
    if update_data.status is not None:
        update_dict["status"] = update_data.status
    if update_data.tags is not None:
        update_dict["tags"] = update_data.tags
    if update_data.description is not None:
        update_dict["description"] = update_data.description

    if update_dict:
        await file_doc.update({"$set": update_dict})
        # Refresh the document
        await file_doc.refresh()

    return FileListResponse(
        id=str(file_doc.id),
        filename=file_doc.filename,
        content_type=file_doc.content_type,
        upload_date=file_doc.upload_date,
        file_size=file_doc.file_size,
        status=file_doc.status,
        owner_id=file_doc.owner_id,
        tags=file_doc.tags,
        description=file_doc.description
    )


@app.delete("/files/{file_id}")
async def delete_file(file_id: str, permanent: bool = Query(False, description="Permanently delete or just mark as deleted")):
    """Delete a file (soft delete by default, permanent if specified)."""
    if not ObjectId.is_valid(file_id):
        raise HTTPException(400, "Invalid file ID")

    # Find the file
    file_doc = await GridFSFile.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(404, "File not found")

    if permanent:
        # Delete from GridFS
        oid = ObjectId(file_id)
        try:
            await gridfs_bucket.delete(oid)
        except Exception as e:
            print(f"Error deleting from GridFS: {e}")

        # Delete from our collection
        await file_doc.delete()
        return {"message": "File permanently deleted", "file_id": file_id}
    else:
        # Soft delete - just mark as deleted
        await file_doc.update({"$set": {"status": FileStatus.DELETED}})
        return {"message": "File marked as deleted", "file_id": file_id, "status": "deleted"}


@app.get("/files", response_model=List[FileListResponse])
async def list_files(
    owner_id: Optional[str] = Query(None, description="Filter by owner ID"),
    status: Optional[FileStatus] = Query(None, description="Filter by file status"),
    content_type: Optional[str] = Query(None, description="Filter by content type (e.g., 'image/', 'video/')"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of files to return"),
    skip: int = Query(0, ge=0, description="Number of files to skip (for pagination)")
) -> List[FileListResponse]:
    """List files with optional filtering and pagination."""

    # Build filter query
    filter_query = {}

    if owner_id:
        filter_query["owner_id"] = owner_id

    if status:
        filter_query["status"] = status

    if content_type:
        filter_query["content_type"] = {"$regex": f"^{content_type}", "$options": "i"}

    # Parse tags filter
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if tag_list:
            filter_query["tags"] = {"$in": tag_list}

    # Query the database collection (not GridFS directly)
    files_cursor = GridFSFile.find(filter_query).skip(skip).limit(limit)
    files = await files_cursor.to_list()

    # Convert to response format
    response_files = []
    for file_doc in files:
        response_files.append(FileListResponse(
            id=str(file_doc.id),
            filename=file_doc.filename,
            content_type=file_doc.content_type,
            upload_date=file_doc.upload_date,
            file_size=file_doc.file_size,
            status=file_doc.status,
            owner_id=file_doc.owner_id,
            tags=file_doc.tags,
            description=file_doc.description
        ))

    return response_files
