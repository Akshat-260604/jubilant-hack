from datetime import datetime
from typing import List, Literal, Optional , Dict
from pydantic import BaseModel, Field


class StateModel(BaseModel):
    current_state: Dict[str, str]
    step_index: Optional[int] = None

class ProcessDocumentsResponse(BaseModel):
    message: str

class VectoriseTextResponse(BaseModel):
    embeddings: List[float]

class GetProcessedDocumentsRequest(BaseModel):
    userId: str

class GetProcessedDocumentsResponse(BaseModel):   
    id: str
    filename: str
    status: str
    createdAt: datetime

class GetMyDocumentDetailsRequest(BaseModel):
    id: str
    userId: str

class MyDocumentExtractedText(BaseModel):
    text: str
    page_number: int

class MyDocumentTables(BaseModel):
    id: str
    page_number: int

class HighlightedImage(BaseModel):
    id: str
    page_number: int

class Summary(BaseModel):
    text: str
    highlighted_image_ids: List[HighlightedImage] 

class GetMyDocumentDetailsResponse(BaseModel):
    id: str
    filename: str
    summary:  Summary
    creation_date: datetime

class ProcessGDriveDocumentsResponse(BaseModel):
    message: str

class ProcessGdriveRequest(BaseModel):
    gdrive_url:str
    userId:str

class VectoriseTextRequest(BaseModel):
    text: str

class GetPresignedUploadUrlResponse(BaseModel):
    presigned_url: str
    uuid: str

class GetPresignedUploadUrlRequest(BaseModel):
    fileName: str
    userId: str

class TriggerProcessingRequest(BaseModel):
    uuid: str
    userId: str

class TriggerProcessingResponse(BaseModel):
    status: str

class GetThumbnailPresignedViewUrlRequest(BaseModel):
    id: str
    userId:str

class GetThumbnailPresignedViewUrlResponse(BaseModel):
    presigned_url: str

class GetTablePresignedViewUrlRequest(BaseModel):
    id: str
    userId: str

class GetTablePresignedViewUrlResponse(BaseModel):
    presigned_url: str

class GetPreviewPagePresignedViewUrlRequest(BaseModel):
    document_id: str
    page_number: int
    userId: str

class GetPreviewPagePresignedViewUrlResponse(BaseModel):
    presigned_url: str

class GetSelfUploadedFilePresignedViewUrlRequest(BaseModel):
    id: str
    userId: str

class GetSelfUploadedFilePresignedViewUrlResponse(BaseModel):
    presigned_url: str

class GetSummaryHighlightImagePresignedViewUrlResponse(BaseModel):
    presigned_url: str  

class GetSummaryHighlightImagePresignedViewUrlRequest(BaseModel):
    id: str
    userId: str

class DeleteDocumentRequest(BaseModel):
    id: str
    userId:str

class DeleteDocumentResponse(BaseModel):
    status: str
    message: str

class ChatRequest(BaseModel):
    prompt: str
    userId: str
    document_ids: List[str]
    creativity_percentage: int
    target_audience: str
    tone: str
    active_voice: bool
    selected_lexica: List[str]
    additional_text: str
    conversation_memory: bool
    context_id: Optional[str] = None
    objective: Optional[str] = None
    content_format: Optional[str] = None
    

class ChatHighlightsRequest(BaseModel):
    userId: str
    document_id: str
    page_number: int
    msg_id: str

class ChatHighlightsResponse(BaseModel):
    presigned_url: str


class StateModel(BaseModel):
    current_state: Dict[str, str]
    step_index: Optional[int] = None

class GenerateSummaryRequest(BaseModel):
    userId: str
    document_id: str

class ImageRequest(BaseModel):
    user_id: str
    document_name: str

class ListTableIdsRequest(BaseModel):
    document_id: str
    user_id: str

class GetDocumentPreviewRequest(BaseModel):
    document_id: str
    user_id: str

class ContentFlowState(BaseModel):
    current_state: Dict[str, str]
    step_index: Optional[int] = None

class ContentGenerationRequest(BaseModel):
    content_format: str
    objective: str
    audience: str
    tone: str
    text: str
    userId: str
    image_paths: Optional[List[str]] = []

class ContentGenerationResponse(BaseModel):
    generated_content: str

class GenerateFindingsRequest(BaseModel):
    content_format: str 
    text: str 


class GenerateFindingsResponse(BaseModel):
    findings: str


class ContentFormatsResponse(BaseModel):
    content_formats: List[str]

class PromptHeadingResponse(BaseModel):
    headings: List[str]

class PromptListResponse(BaseModel):
    heading: str
    prompts: List[str]


# 11-07-2025 Changes Made by me

class CreateWorkspaceRequest(BaseModel):
    user_id: str
    name: str
    files: List[str] = Field(default_factory=list)
    type: Literal["contextual", "instant"]

class CreateWorkspaceResponse(BaseModel):
    workspace_id:str

class FileInfo(BaseModel):
    id:str
    filename:str
    createdAt:str

class GetWorkspaceFilesResponse(BaseModel):
    name:str
    type: Literal["contextual", "instant"]
    files: List[FileInfo]

class WorkspaceInfo(BaseModel):
    id: str
    name: str
    type: str
    createdAt: datetime
    fileCount: int  # optional, helpful for frontend
    filenames: List[str] = []

class UserWorkspacesResponse(BaseModel):
    workspaces: List[WorkspaceInfo]