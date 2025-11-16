# routes/workspace.py

from fastapi import APIRouter, HTTPException
from models.workspace import WorkspaceModel, workspace_repo
from schemas.base import CreateWorkspaceRequest, CreateWorkspaceResponse ,GetWorkspaceFilesResponse, FileInfo, UserWorkspacesResponse, WorkspaceInfo
from datetime import datetime, timezone
from models.doc import doc_repo
from uuid import uuid4

router = APIRouter()

@router.post("/create-workspace", response_model=CreateWorkspaceResponse)
async def create_workspace(
    payload: CreateWorkspaceRequest
):
    try:
        # Create a unique Mongo-style string ID
        workspace_id = str(uuid4())
        now = datetime.now(timezone.utc)  

        new_workspace = WorkspaceModel(
            id=workspace_id,
            user_id=payload.user_id,
            name=payload.name,
            type=payload.type,
            created_at=now,
            updated_at=now,
            files=payload.files
        )

        inserted_id = await workspace_repo.add_new_workspace(new_workspace)

        return CreateWorkspaceResponse(
            workspace_id=inserted_id,
            message="Workspace created successfully.",
            created_at=now
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-workspace-files", response_model=GetWorkspaceFilesResponse)
async def get_workspace_files(workspace_id: str):
    # Step 1: Fetch workspace by ID
    workspace = await workspace_repo.get_workspace_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Step 2: Collect file metadata
    files = []
    for file_id in workspace.get("files", []):
        doc = await doc_repo.get_doc_by_id(file_id)
        if doc:
            files.append(FileInfo(
                id=file_id,
                filename=doc["filename"],
                createdAt=doc["creation_date"]  # Or use raw datetime if desired
            ))

    return GetWorkspaceFilesResponse(
        name=workspace["name"],
        type=workspace["type"],
        files=files
    )

@router.get("/list-user-workspaces", response_model=UserWorkspacesResponse)
async def list_user_workspaces(user_id: str):
    workspaces = await workspace_repo.get_workspaces_by_user_id(user_id)
    if not workspaces:
        return UserWorkspacesResponse(workspaces=[])

    formatted_workspaces = []
    for ws in workspaces:
        workspace_id = ws.get("_id")
        if not workspace_id:
            continue

        file_ids = ws.get("files", [])
        filenames = []

        # Fetch filename for each file ID
        for file_id in file_ids:
            doc = await doc_repo.get_doc_by_id(file_id)
            if doc and "filename" in doc:
                filenames.append(doc["filename"])

        formatted_workspaces.append(WorkspaceInfo(
            id=str(workspace_id),
            name=ws["name"],
            type=ws["type"],
            createdAt=ws["created_at"],
            fileCount=len(file_ids),
            filenames=filenames  # new field
        ))

    return UserWorkspacesResponse(workspaces=formatted_workspaces)

@router.post("/delete-workspace")
async def delete_workspace(workspace_id: str):
    try:
        deleted = await workspace_repo.delete_workspace(workspace_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Workspace not found or could not be deleted")
        return {"message": "Workspace deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

