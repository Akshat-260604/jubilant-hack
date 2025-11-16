from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from services.google_drive_service import google_drive_service, DriveDocument
from lib.hasher import hash_param
from utils.document_handling.logger import log
from configs.config import google_drive_settings

router = APIRouter()

# Pydantic models for request/response
class DriveSetupResponse(BaseModel):
    """Response model for Google Drive setup."""
    success: bool
    message: str
    folder_id: Optional[str] = None

class DriveDocumentResponse(BaseModel):
    """Response model for Drive document information."""
    document_id: str
    name: str
    mime_type: str
    modified_time: str
    web_view_link: str
    size: Optional[int] = None
    source_type: str = "google_drive"

class DriveListResponse(BaseModel):
    """Response model for listing Drive documents."""
    success: bool
    documents: List[DriveDocumentResponse]
    total_count: int

class DriveSyncRequest(BaseModel):
    """Request model for syncing Drive documents."""
    userId: str
    force_resync: bool = False

class DriveSyncResponse(BaseModel):
    """Response model for Drive sync operation."""
    success: bool
    message: str
    synced_document_ids: List[str]
    total_synced: int

class DriveDocumentRequest(BaseModel):
    """Request model for accessing specific Drive document."""
    userId: str
    file_id: str

class DriveDocumentContentResponse(BaseModel):
    """Response model for Drive document content."""
    success: bool
    file_id: str
    filename: str
    content_size: int
    download_url: Optional[str] = None

@router.post("/google-drive/setup", response_model=DriveSetupResponse)
async def setup_google_drive():
    """
    Set up and test Google Drive API connection.

    Returns:
        DriveSetupResponse: Setup status and configuration info
    """
    try:
        # Check if Google Drive is configured
        if not google_drive_settings.is_configured:
            return DriveSetupResponse(
                success=False,
                message=(
                    "Google Drive is not configured. Please set up the following environment variables: "
                    "GOOGLE_DRIVE_FOLDER_ID and ensure the service account key file exists at "
                    f"{google_drive_settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH}"
                ),
                folder_id=google_drive_settings.GOOGLE_DRIVE_FOLDER_ID
            )

        # Test authentication
        auth_success = await google_drive_service.authenticate()

        if not auth_success:
            return DriveSetupResponse(
                success=False,
                message="Failed to authenticate with Google Drive API. Check service account credentials."
            )

        # Test folder access
        try:
            documents = await google_drive_service.list_medical_documents()

            return DriveSetupResponse(
                success=True,
                message=f"Google Drive setup successful. Found {len(documents)} accessible documents.",
                folder_id=google_drive_settings.GOOGLE_DRIVE_FOLDER_ID
            )
        except Exception as folder_error:
            return DriveSetupResponse(
                success=False,
                message=f"Authentication successful but folder access failed: {str(folder_error)}"
            )

    except Exception as e:
        log(f"Google Drive setup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")

@router.get("/google-drive/documents", response_model=DriveListResponse)
async def list_google_drive_documents():
    """
    List all medical documents available in the configured Google Drive folder.

    Returns:
        DriveListResponse: List of available documents
    """
    try:
        documents = await google_drive_service.list_medical_documents()

        document_responses = [
            DriveDocumentResponse(
                document_id=doc.document_id,
                name=doc.name,
                mime_type=doc.mime_type,
                modified_time=doc.modified_time,
                web_view_link=doc.web_view_link,
                size=doc.size
            )
            for doc in documents
        ]

        return DriveListResponse(
            success=True,
            documents=document_responses,
            total_count=len(document_responses)
        )

    except Exception as e:
        log(f"Error listing Google Drive documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.post("/google-drive/sync", response_model=DriveSyncResponse)
async def sync_google_drive_documents(request: DriveSyncRequest, background_tasks: BackgroundTasks):
    """
    Sync Google Drive documents to the local system for search indexing.

    Args:
        request (DriveSyncRequest): Sync parameters including user ID
        background_tasks (BackgroundTasks): For running sync in background

    Returns:
        DriveSyncResponse: Sync operation results
    """
    try:
        userId = request.userId

        if not userId or not userId.strip():
            raise HTTPException(status_code=400, detail="userId is required")

        # Hash the user ID for consistency with existing system
        userId = await hash_param(userId)

        # Run sync operation
        synced_ids = await google_drive_service.sync_drive_documents()

        return DriveSyncResponse(
            success=True,
            message=f"Successfully synced {len(synced_ids)} Google Drive documents",
            synced_document_ids=synced_ids,
            total_synced=len(synced_ids)
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        log(f"Error syncing Google Drive documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.post("/google-drive/document/content", response_model=DriveDocumentContentResponse)
async def get_google_drive_document_content(request: DriveDocumentRequest):
    """
    Get content of a specific Google Drive document.

    Args:
        request (DriveDocumentRequest): Request with file ID and user ID

    Returns:
        DriveDocumentContentResponse: Document content information
    """
    try:
        userId = request.userId
        file_id = request.file_id

        if not userId or not userId.strip():
            raise HTTPException(status_code=400, detail="userId is required")

        if not file_id or not file_id.strip():
            raise HTTPException(status_code=400, detail="file_id is required")

        # Hash the user ID for consistency
        userId = await hash_param(userId)

        # Download document content
        result = await google_drive_service.download_document_content(file_id)

        if result is None:
            raise HTTPException(status_code=404, detail="Document not found or download failed")

        content, filename = result

        # Get shareable link
        shareable_link = await google_drive_service.get_shareable_link(file_id)

        return DriveDocumentContentResponse(
            success=True,
            file_id=file_id,
            filename=filename,
            content_size=len(content),
            download_url=shareable_link
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        log(f"Error getting Google Drive document content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document content: {str(e)}")

@router.get("/google-drive/document/{file_id}/link")
async def get_google_drive_document_link(file_id: str):
    """
    Get a shareable link for a Google Drive document (for citations).

    Args:
        file_id (str): Google Drive file ID

    Returns:
        dict: Shareable link information
    """
    try:
        if not file_id or not file_id.strip():
            raise HTTPException(status_code=400, detail="file_id is required")

        link = await google_drive_service.get_shareable_link(file_id)

        if not link:
            raise HTTPException(status_code=404, detail="Document not found or link unavailable")

        return {
            "success": True,
            "file_id": file_id,
            "shareable_link": link,
            "link_type": "google_drive"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log(f"Error getting Google Drive document link: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document link: {str(e)}")

@router.get("/google-drive/health")
async def google_drive_health_check():
    """
    Health check endpoint for Google Drive integration.

    Returns:
        dict: Health status of Google Drive service
    """
    try:
        # Test authentication
        auth_success = await google_drive_service.authenticate()

        if auth_success:
            # Quick test to list a few documents
            documents = await google_drive_service.list_medical_documents()

            return {
                "success": True,
                "status": "healthy",
                "authenticated": True,
                "accessible_documents": len(documents),
                "timestamp": "2024-11-13T12:00:00Z"
            }
        else:
            return {
                "success": False,
                "status": "authentication_failed",
                "authenticated": False,
                "error": "Failed to authenticate with Google Drive API"
            }

    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "authenticated": False,
            "error": str(e)
        }