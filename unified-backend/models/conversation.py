from pydantic import BaseModel, Field
from bson import ObjectId
from services.document_db import get_database
from typing import List, Dict, Literal, Optional

class ConversationModel(BaseModel):
    """
    Pydantic model for conversation data validation and serialization.

    Attributes:
        document_id (List[str]): List of document IDs associated with the conversation
        message_ids (List[str]): List of message IDs in the conversation thread
    """
    document_id: List[str] 
    message_ids: List[str] = Field(default_factory=list)

class HighlightModel(BaseModel):
    """
    Pydantic model for document highlighting metadata.

    Attributes:
        message_id (str): ID of the message containing the highlight
        document_id (str): ID of the document being highlighted
        page_number (int): Page number where the highlight appears
        status (Literal['pending', 'done', 'error']): Processing status of the highlight
    """
    message_id: str
    document_id: str  
    page_number: int
    status: Literal['pending', 'done', 'error'] = Field(default='pending')

class MessageModel(BaseModel):
    """
    Pydantic model for chat messages.

    Attributes:
        id (str): Unique message identifier (used as _id in MongoDB)
        user_message (Optional[str]): Content of the user's message
        assistant_message (Optional[str]): Content of the assistant's response
    """
    id: str
    user_message: Optional[str] = None
    assistant_message: Optional[str] = None

class ConversationRepository:
    """
    Repository class for managing conversations, messages, and highlights in MongoDB.

    Handles CRUD operations for:
    - Conversations and their associated documents
    - User and assistant messages
    - Document highlights and their status

    Attributes:
        conversation_collection: MongoDB collection for conversations
        message_collection: MongoDB collection for messages
        highlight_collection: MongoDB collection for highlights
    """

    def __init__(self, database):
        """
        Initialize ConversationRepository with database collections.

        Args:
            database: MongoDB database instance
        """
        self.conversation_collection = database['conversations']
        self.message_collection = database['messages']
        self.highlight_collection = database['highlights']
    
    async def create_conversation(self, document_ids: List[str]) -> str:
        """
        Create a new conversation entry.

        Args:
            document_ids (List[str]): List of document IDs to associate with conversation

        Returns:
            str: Generated context_id for the new conversation
        """
        conversation = {
            "document_id": document_ids,
            "message_ids": []
        }
        result = await self.conversation_collection.insert_one(conversation)
        return str(result.inserted_id)
    
    async def add_or_update_message(self, context_id: str, message_id: str, role: str, message: str):
        """
        Add or update a message in a conversation.

        Args:
            context_id (str): Conversation context ID
            message_id (str): Unique message identifier
            role (str): Message sender role ('user' or 'assistant')
            message (str): Message content

        Notes:
            - Updates existing message if message_id exists
            - Adds message_id to conversation's message_ids list for user messages
        """
        query = {"_id": message_id}
        update_field = "user_message" if role == "user" else "assistant_message"
        update = {"$set": {update_field: message}}
        
        await self.message_collection.update_one(query, update, upsert=True)
        
        if role == "user":
            await self.conversation_collection.update_one(
                {"_id": ObjectId(context_id)},
                {"$push": {"message_ids": message_id}},
                upsert=True
            )
    
    async def update_highlight_status(self, message_id: str, document_id: str, page_number: int, status: str):
        """
        Update the status of a document highlight.

        Args:
            message_id (str): ID of the message containing the highlight
            document_id (str): ID of the document being highlighted
            page_number (int): Page number of the highlight
            status (str): New status ('done', 'pending', or 'error')

        Raises:
            ValueError: If status is not one of the allowed values
        """
        if status not in ["done", "pending", "error"]:
            raise ValueError("Invalid status. Choose from: done, pending, error")
        
        query = {"message_id": message_id, "document_id": document_id, "page_number": page_number}
        update = {"$set": {"status": status}}
        await self.highlight_collection.update_one(query, update, upsert=True)
    
    async def get_highlight_status(self, message_id: str, document_id: str, page_number: int) -> Optional[str]:
        """Fetches the highlight status of a message for a specific page number, considering document ID."""
        result = await self.highlight_collection.find_one({"message_id": message_id, "document_id": document_id, "page_number": page_number}, {"status": 1})
        return result.get("status") if result else "pending"
    
    async def add_highlight(self, message_id: str, document_id: str, page_number: int, status: str = "pending"):
        """Adds a new highlight entry for a message with a specific page number and document ID."""
        highlight = {
            "message_id": message_id,
            "document_id": document_id,
            "page_number": page_number,
            "status": status
        }
        await self.highlight_collection.insert_one(highlight)
    
    async def get_messages_by_context(self, context_id: str, limit: int = 6) -> List[Dict[str, str]]:
        """Fetches the last `limit` messages linked to a context_id. If limit is None or 0, fetches all messages."""
        conversation = await self.conversation_collection.find_one({"_id": ObjectId(context_id)})
        if not conversation:
            return []
        
        message_ids = conversation.get("message_ids", [])  
        if limit and limit > 0:
            message_ids = message_ids[-limit:]  # Fetch only the last `limit` messages 
            messages = await self.message_collection.find({"_id": {"$in": message_ids}}).to_list(None)

            # Sort messages to maintain order
            message_dict = {msg["_id"]: msg for msg in messages}
            ordered_messages = [message_dict[msg_id] for msg_id in message_ids if msg_id in message_dict]

            # Remove '_id' field from each message
            return [{k: v for k, v in msg.items() if k != "_id"} for msg in ordered_messages]

        return []
    
    async def delete_conversations_by_document(self, document_id: str):
        """Deletes all conversations, messages, and highlights associated with a given document_id."""
        conversations = await self.conversation_collection.find({"document_id": {"$in": [document_id]}}).to_list(None)
        message_ids = [msg_id for conv in conversations for msg_id in conv.get("message_ids", [])]
        
        await self.conversation_collection.delete_many({"document_id": {"$in": [document_id]}})
        await self.message_collection.delete_many({"_id": {"$in": message_ids}})
        await self.highlight_collection.delete_many({"document_id": document_id})
    
# Initialize repository
db = get_database()
conversation_repo = ConversationRepository(db)