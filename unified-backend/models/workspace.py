from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Literal, Optional
from services.document_db import get_database


class WorkspaceModel(BaseModel):
    """
    Pydantic model representing a workspace document.

    Attributes
    ----------
    id : str
        Unique workspace ID (MongoDB _id as a string).
    user_id : str
        ID of the user who owns the workspace.
    name : str
        Human‑readable workspace name.
    files : List[str]
        List of file IDs associated with this workspace.
    created_at : datetime
        Timestamp when the workspace was created.
    updated_at : datetime
        Timestamp when the workspace was last updated.
    """
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    name: str
    type: Literal["contextual", "instant"]  
    files: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True

class WorkspaceRepository:
    """
    Repository for CRUD operations on the `workspaces` collection.
    """

    def __init__(self, database):
        self.collection = database["workspaces"]

    async def add_new_workspace(self, workspace_data: WorkspaceModel) -> str:
        """
        Insert a new workspace.
        Parameters
        ----------
        workspace_data: WorkspaceModel Data for the new workspace.
        Returns
        -------
        str
            Inserted workspace ID.
        """
        data = workspace_data.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)


    async def get_workspace_by_id(self, workspace_id: str) -> Optional[dict]:
        """
        Fetch a single workspace by its ID.
        Returns None if not found.
        """
        return await self.collection.find_one({"_id": workspace_id}, {"_id": 0})

    async def get_workspaces_by_user_id(self, user_id: str) -> List[dict]:
        """
        Fetch all workspaces belonging to a user.
        """
        cursor = self.collection.find({"user_id": user_id})
        return await cursor.to_list(length=None)

    async def update_workspace_name(self, workspace_id: str, new_name: str) -> bool:
        """
        Update the workspace's name.
        Returns True if a document was modified.
        """
        result = await self.collection.update_one(
            {"_id": workspace_id},
            {
                "$set": {
                    "name": new_name,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count == 1

    async def delete_workspace(self, workspace_id: str) -> bool:
        """
        Delete a workspace (soft‑delete pattern could be implemented here).
        Returns True if a document was deleted.
        """
        result = await self.collection.delete_one({"_id": workspace_id})
        return result.deleted_count == 1

    async def count_workspaces_by_user(self, user_id: str) -> int:
        """
        Count workspaces for a given user.
        """
        return await self.collection.count_documents({"user_id": user_id})


db = get_database()
workspace_repo = WorkspaceRepository(db)