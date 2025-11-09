import os
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

from app.models.file import GridFSFile

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://root:example@localhost:27017")
DB_NAME = os.getenv("DB_NAME", "media_db")


client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

gridfs_bucket = AsyncIOMotorGridFSBucket(db)


async def init_db():
    await init_beanie(database=db, document_models=[GridFSFile])
