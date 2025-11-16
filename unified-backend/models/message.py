import asyncio
from datetime import datetime, timezone
from bson.objectid import ObjectId, InvalidId
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional
from services.document_db import get_database

class AssistantMessage(BaseModel):
    msg: str
    source_index: List[int]

class MessageModel(BaseModel):
    # _id: ObjectId created by mongo
    context_id: str
    workspace_id: str = Field(default=None) #TODO : to be removed with v1 removed
    user_message: str
    assistant_message: Optional[List[AssistantMessage]] = Field(default_factory=list)
    complete_response: Optional[str] = Field(default=None)
    created_at: datetime=Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["success", "error", "pending"] = Field(default="pending")

class MessageRepository:
    def __init__(self, database):
        self.collection = database['messages']
        asyncio.create_task(self._ensure_indexes())

    async def _ensure_indexes(self):
        """Create indexes only for fields used in queries."""
        # For retrieving recent messages by context_id efficiently
        await self.collection.create_index(
            [("context_id", 1), ("created_at", -1)]
        )

    async def create_message(self, message: MessageModel):
        result = await self.collection.insert_one(message.model_dump(by_alias=True))
        return str(result.inserted_id)
    
    async def get_message(self, message_id: str):
        try:
            object_id = ObjectId(message_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid project ID")

        message = await self.collection.find_one({"_id": object_id},{"_id": 0, "context_id": 1, "workspace_id": 1})
        return message
    

    async def get_messages_by_workspace_id(self, workspace_id: str, limit: int, before_timestamp: Optional[datetime]):
        query = {"workspace_id": workspace_id}
        if before_timestamp:
            query["created_at"] = {"$lt": before_timestamp}

        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)  # newest first
            .limit(limit)
        )
        messages = await cursor.to_list(length=limit)
        for message in messages:
            message["message_id"] = str(message["_id"])
            message["created_at"] = message["created_at"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return messages
    
    async def get_time_stamp_of_first_message(self, workspace_id: str):
        result = await self.collection.find({"workspace_id": workspace_id}).sort("created_at", 1).limit(1).to_list(length=1)
        if result:
            return result[0]["created_at"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return None
    
    async def get_assistant_message(self, message_id: str):
        try:
            object_id = ObjectId(message_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid project ID")

        message = await self.collection.find_one({"_id": object_id},{"_id": 0, "assistant_message": 1})
        if message:
            return message["assistant_message"]
        return None

    async def add_assistant_message(self, message_id: str, assistant_message: AssistantMessage):

        await self.collection.update_one({"_id": ObjectId(message_id)}, {"$push": {"assistant_message": assistant_message.model_dump(by_alias=True)}})

    async def add_complete_response(self, message_id: str, complete_response: str,status:str="success"):
        await self.collection.update_one({"_id": message_id}, {"$set": {"complete_response": complete_response,"status":status}})

    async def get_messages(self, context_id: str, limit: int=3):
        projection = {"_id": 0, "user_message": 1, "complete_response": 1 }
        messages = await self.collection.find({"context_id": context_id}, projection).sort("created_at", -1).limit(limit).to_list(length=limit)
        return messages
    
db=get_database()
message_repo = MessageRepository(db)