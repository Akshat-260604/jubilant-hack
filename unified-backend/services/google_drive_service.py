import os
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import io
import logging
from concurrent.futures import ThreadPoolExecutor

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from configs.config import google_drive_settings
from services.qdrant_host import current_qdrant_client
from services.document_encoder import DocumentEncoder
from utils.document_handling.process_document import add_document_to_collection, DOCUMENT_TEXT_COLLECTION_NAME

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriveDocument:
    """Represents a document from Google Drive with metadata."""

    def __init__(self, file_id: str, name: str, mime_type: str, modified_time: str,
                 web_view_link: str, size: Optional[int] = None):
        self.file_id = file_id
        self.name = name
        self.mime_type = mime_type
        self.modified_time = modified_time
        self.web_view_link = web_view_link
        self.size = size
        self.document_id = f"drive_{file_id}"

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "file_id": self.file_id,
            "document_id": self.document_id,
            "name": self.name,
            "mime_type": self.mime_type,
            "modified_time": self.modified_time,
            "web_view_link": self.web_view_link,
            "size": self.size,
            "source_type": "google_drive"
        }

class GoogleDriveService:
    """
    Service to interact with Google Drive API for medical document management.
    Provides functionality to list, download, and index medical documents from a shared Drive folder.
    """

    def __init__(self):
        self.service = None
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self._supported_mime_types = {
            'application/pdf': '.pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.ms-excel': '.xls',
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/gif': '.gif',
            'text/plain': '.txt'
        }

    async def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API using service account.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Check if Google Drive is configured
            if not google_drive_settings.is_configured:
                logger.warning("Google Drive is not properly configured. Skipping authentication.")
                return False

            # Check if service account key file exists
            key_path = google_drive_settings.GOOGLE_SERVICE_ACCOUNT_KEY_PATH
            if not os.path.exists(key_path):
                logger.error(f"Service account key file not found at: {key_path}")
                return False

            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )

            # Build Drive API service
            self.service = build('drive', 'v3', credentials=credentials)

            # Test connection
            await self._test_connection()
            logger.info("Google Drive authentication successful")
            return True

        except Exception as e:
            logger.error(f"Google Drive authentication failed: {str(e)}")
            return False

    async def _test_connection(self):
        """Test the Google Drive API connection."""
        loop = asyncio.get_event_loop()
        try:
            # Test with a simple API call
            await loop.run_in_executor(
                self.thread_pool,
                lambda: self.service.files().list(pageSize=1).execute()
            )
        except Exception as e:
            raise Exception(f"Google Drive connection test failed: {str(e)}")

    async def list_medical_documents(self, folder_id: Optional[str] = None) -> List[DriveDocument]:
        """
        List all medical documents from the specified Google Drive folder.

        Args:
            folder_id (Optional[str]): Drive folder ID. If None, uses configured folder ID.

        Returns:
            List[DriveDocument]: List of medical documents found
        """
        # Check if Google Drive is configured
        if not google_drive_settings.is_configured:
            logger.warning("Google Drive is not configured. Cannot list documents.")
            return []

        if not self.service:
            if not await self.authenticate():
                return []

        folder_id = folder_id or google_drive_settings.GOOGLE_DRIVE_FOLDER_ID

        if not folder_id:
            logger.error("No Google Drive folder ID configured")
            return []

        try:
            # Query to get all files in the folder with supported formats
            mime_types = list(self._supported_mime_types.keys())
            mime_query = " or ".join([f"mimeType='{mt}'" for mt in mime_types])

            query = f"'{folder_id}' in parents and ({mime_query}) and trashed=false"

            loop = asyncio.get_event_loop()

            def _list_files():
                files = []
                page_token = None

                while True:
                    results = self.service.files().list(
                        q=query,
                        spaces='drive',
                        fields='nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink, size)',
                        pageToken=page_token,
                        pageSize=100
                    ).execute()

                    files.extend(results.get('files', []))
                    page_token = results.get('nextPageToken')

                    if not page_token:
                        break

                return files

            files = await loop.run_in_executor(self.thread_pool, _list_files)

            # Convert to DriveDocument objects
            documents = []
            for file in files:
                doc = DriveDocument(
                    file_id=file['id'],
                    name=file['name'],
                    mime_type=file['mimeType'],
                    modified_time=file['modifiedTime'],
                    web_view_link=file['webViewLink'],
                    size=file.get('size')
                )
                documents.append(doc)

            logger.info(f"Found {len(documents)} medical documents in Google Drive")
            return documents

        except HttpError as e:
            logger.error(f"Google Drive API error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error listing Google Drive documents: {str(e)}")
            return []

    async def download_document_content(self, file_id: str) -> Optional[Tuple[bytes, str]]:
        """
        Download content of a specific document from Google Drive.

        Args:
            file_id (str): Google Drive file ID

        Returns:
            Optional[Tuple[bytes, str]]: (file_content, filename) or None if failed
        """
        if not self.service:
            if not await self.authenticate():
                return None

        try:
            loop = asyncio.get_event_loop()

            def _download_file():
                # Get file metadata
                file_metadata = self.service.files().get(fileId=file_id).execute()
                filename = file_metadata['name']

                # Download file content
                request = self.service.files().get_media(fileId=file_id)
                file_io = io.BytesIO()
                downloader = MediaIoBaseDownload(file_io, request)

                done = False
                while done is False:
                    status, done = downloader.next_chunk()

                file_content = file_io.getvalue()
                return file_content, filename

            content, filename = await loop.run_in_executor(self.thread_pool, _download_file)
            logger.info(f"Downloaded document: {filename} ({len(content)} bytes)")
            return content, filename

        except HttpError as e:
            logger.error(f"Google Drive download error for file {file_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error downloading document {file_id}: {str(e)}")
            return None

    async def get_shareable_link(self, file_id: str) -> Optional[str]:
        """
        Get a shareable link for a Google Drive document.

        Args:
            file_id (str): Google Drive file ID

        Returns:
            Optional[str]: Shareable link or None if failed
        """
        if not self.service:
            if not await self.authenticate():
                return None

        try:
            loop = asyncio.get_event_loop()

            def _get_link():
                file_metadata = self.service.files().get(
                    fileId=file_id,
                    fields='webViewLink'
                ).execute()
                return file_metadata.get('webViewLink')

            link = await loop.run_in_executor(self.thread_pool, _get_link)
            return link

        except Exception as e:
            logger.error(f"Error getting shareable link for file {file_id}: {str(e)}")
            return None

    async def sync_drive_documents(self) -> List[str]:
        """
        Sync Google Drive documents to the local system and process them for embeddings.
        Downloads content, extracts text, and stores in the same 'creator' collection as other documents.

        Returns:
            List[str]: List of document IDs that were synced and processed
        """
        documents = await self.list_medical_documents()
        synced_ids = []

        for doc in documents:
            try:
                logger.info(f"Processing Google Drive document: {doc.name} (ID: {doc.document_id})")

                # Download document content
                content_result = await self.download_document_content(doc.file_id)
                if content_result is None:
                    logger.warning(f"Failed to download content for {doc.name}")
                    continue

                content, filename = content_result

                # Extract text from document using existing extraction pipeline
                extracted_text = ""
                if doc.mime_type == 'application/pdf':
                    # Extract text from PDF using existing extraction logic
                    try:
                        from utils.document_handling.extraction_engine import extract_text_from_pdf_data_for_vectorisation
                        extracted_text = await extract_text_from_pdf_data_for_vectorisation(content, filename, "google_drive_sync")
                    except Exception as e:
                        logger.error(f"Failed to extract text from PDF {doc.name}: {str(e)}")
                        continue
                elif doc.mime_type == 'text/plain':
                    extracted_text = content.decode('utf-8')
                elif doc.mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                    # For Word documents, you might want to add docx/doc parsing here
                    logger.warning(f"Word document processing not yet implemented for: {doc.name}")
                    continue
                elif doc.mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
                    # For Excel documents, you might want to add xlsx/xls parsing here
                    logger.warning(f"Excel document processing not yet implemented for: {doc.name}")
                    continue
                else:
                    logger.warning(f"Unsupported document type for text extraction: {doc.mime_type} ({doc.name})")
                    continue

                if not extracted_text.strip():
                    logger.warning(f"No text extracted from {doc.name}")
                    continue

                # Add to the same 'creator' collection using existing pipeline
                add_document_to_collection(extracted_text, doc.document_id)

                logger.info(f"Successfully processed and embedded: {doc.name} (ID: {doc.document_id})")
                synced_ids.append(doc.document_id)

            except Exception as e:
                logger.error(f"Error processing Google Drive document {doc.name}: {str(e)}")

        logger.info(f"Successfully processed {len(synced_ids)} Google Drive documents into 'creator' collection")
        return synced_ids

    def is_supported_format(self, mime_type: str) -> bool:
        """
        Check if the document format is supported for processing.

        Args:
            mime_type (str): MIME type of the document

        Returns:
            bool: True if format is supported
        """
        return mime_type in self._supported_mime_types

    async def close(self):
        """Clean up resources."""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)

# Global instance
google_drive_service = GoogleDriveService()