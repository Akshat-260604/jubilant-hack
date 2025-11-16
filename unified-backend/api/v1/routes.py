from fastapi import APIRouter

# Chat / search endpoints (from chat-fun)
from api.v1.endpoints.chat import router as chat_router
from api.v1.endpoints.smart_chat import router as smart_chat_router
from api.v1.endpoints.translation import router as translation_router
from api.v1.endpoints.rephraser import router as rephraser_router
from api.v1.endpoints.airewrite import router as airewriter_router
from api.v1.endpoints.chat_highlight import router as chat_highlight_router

# Document & Google Drive endpoints (from src12)
from api.v1.endpoints.get_presigned_url import router as get_presigned_url_router
from api.v1.endpoints.trigger_process_document import router as trigger_process_document_router
from api.v1.endpoints.get_processed_documents import router as get_processed_documents_router
from api.v1.endpoints.get_preview import router as get_preview_router
from api.v1.endpoints.google_drive import router as google_drive_router
from api.v1.endpoints.documents_upload import router as documents_upload_router
from api.v1.endpoints.reports import router as reports_router


router = APIRouter()

# Chat & assistance features
router.include_router(chat_router)
router.include_router(smart_chat_router)
router.include_router(translation_router)
router.include_router(rephraser_router)
router.include_router(airewriter_router)
router.include_router(chat_highlight_router)

# Document upload & processing features used (or declared) in the frontend API client
router.include_router(documents_upload_router)
router.include_router(get_presigned_url_router)
router.include_router(trigger_process_document_router)
router.include_router(get_processed_documents_router)
router.include_router(get_preview_router)
router.include_router(google_drive_router)

# Report generation endpoints referenced by the frontend API client
router.include_router(reports_router)


@router.get("/health_check")
def health_check():
    return {
        "statusCode": 200,
        "message": "Server is running successfully",
        "version": 1,
    }