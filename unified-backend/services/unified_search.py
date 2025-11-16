import asyncio
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

from services.qdrant_host import current_qdrant_client
from utils.chat.vectorise_text import vectorise_text

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentSource(Enum):
    """Enum for document source types."""
    UPLOADED = "uploaded"
    GOOGLE_DRIVE = "google_drive"

@dataclass
class SearchResult:
    """Represents a search result from any document source."""
    document_id: str
    document_name: str
    source_type: DocumentSource
    content: str
    score: float
    page_number: Optional[int] = None
    shareable_link: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "source_type": self.source_type.value,
            "content": self.content,
            "score": self.score,
            "page_number": self.page_number,
            "shareable_link": self.shareable_link,
            "metadata": self.metadata
        }

class UnifiedSearchService:
    """
    Service that provides unified search across both uploaded documents
    and Google Drive documents for intelligent auto-discovery.
    """

    def __init__(self):
        self.unified_collection = "creator"  # Both uploaded and Google Drive docs are in same collection

    async def search_all_sources(
        self,
        query: str,
        max_results: int = 20,
        score_threshold: float = 0.6,
        include_uploaded: bool = True,
        include_drive: bool = True
    ) -> List[SearchResult]:
        """
        Search across unified collection containing both uploaded and Google Drive documents.

        Args:
            query (str): Search query text
            max_results (int): Maximum number of results to return
            score_threshold (float): Minimum similarity score threshold
            include_uploaded (bool): Whether to include uploaded documents (ignored - unified search)
            include_drive (bool): Whether to include Google Drive documents (ignored - unified search)

        Returns:
            List[SearchResult]: Ranked search results from unified collection
        """
        try:
            # Generate query embedding
            query_embedding = await vectorise_text(query)

            # Search in unified collection (contains both uploaded and Google Drive docs)
            search_result = current_qdrant_client.search(
                collection_name=self.unified_collection,
                query_vector=query_embedding,
                limit=max_results * 2  # Get more to ensure good results after filtering
            )

            results = []
            for point in search_result:
                try:
                    payload = point.payload
                    document_id = payload.get("document_id", "unknown")

                    # Determine source type based on document_id prefix
                    if document_id.startswith("drive_"):
                        source_type = DocumentSource.GOOGLE_DRIVE
                        document_name = payload.get("document_name", "Unknown Drive Document")
                    else:
                        source_type = DocumentSource.UPLOADED
                        document_name = payload.get("document_name", "Unknown Document")

                    # Skip if score below threshold
                    if point.score < score_threshold:
                        continue

                    result = SearchResult(
                        document_id=document_id,
                        document_name=document_name,
                        source_type=source_type,
                        content=payload.get("text", ""),
                        score=point.score,
                        page_number=payload.get("page_number"),
                        shareable_link=payload.get("web_view_link"),  # For Google Drive docs
                        metadata={
                            "collection": self.unified_collection,
                            "point_id": point.id,
                            "file_id": payload.get("file_id")  # For Google Drive docs
                        }
                    )
                    results.append(result)

                except Exception as e:
                    logger.error(f"Error processing search result: {str(e)}")
                    continue

            # Sort by score (highest first) and limit results
            ranked_results = sorted(results, key=lambda x: x.score, reverse=True)[:max_results]

            logger.info(f"Found {len(ranked_results)} relevant documents for query: '{query[:50]}...'")
            return ranked_results

        except Exception as e:
            logger.error(f"Error searching unified collection: {str(e)}")
            return []


    async def get_relevant_document_ids(
        self,
        query: str,
        max_docs: int = 5,
        score_threshold: float = 0.7
    ) -> Tuple[List[str], List[str]]:
        """
        Get document IDs that are relevant to the query for RAG processing.

        Args:
            query (str): Search query
            max_docs (int): Maximum number of documents to return
            score_threshold (float): Minimum relevance score

        Returns:
            Tuple[List[str], List[str]]: (uploaded_doc_ids, drive_doc_ids)
        """
        # Search across all sources
        results = await self.search_all_sources(
            query=query,
            max_results=max_docs * 2,  # Get more to ensure we have enough after filtering
            score_threshold=score_threshold
        )

        uploaded_doc_ids = []
        drive_doc_ids = []

        # Separate by source type
        for result in results[:max_docs]:
            if result.source_type == DocumentSource.UPLOADED:
                if result.document_id not in uploaded_doc_ids:
                    uploaded_doc_ids.append(result.document_id)
            elif result.source_type == DocumentSource.GOOGLE_DRIVE:
                if result.document_id not in drive_doc_ids:
                    drive_doc_ids.append(result.document_id)

        logger.info(f"Auto-discovered {len(uploaded_doc_ids)} uploaded docs and {len(drive_doc_ids)} Drive docs")
        return uploaded_doc_ids, drive_doc_ids

    async def format_mixed_context(
        self,
        query: str,
        max_chunks: int = 15,
        score_threshold: float = 0.6
    ) -> str:
        """
        Create formatted context string from both uploaded and Drive documents.

        Args:
            query (str): Search query
            max_chunks (int): Maximum text chunks to include
            score_threshold (float): Minimum relevance score

        Returns:
            str: Formatted context string for RAG processing
        """
        # Get relevant search results
        results = await self.search_all_sources(
            query=query,
            max_results=max_chunks,
            score_threshold=score_threshold
        )

        context_parts = []

        for result in results:
            # Format each chunk with source attribution
            source_prefix = "📁 Drive:" if result.source_type == DocumentSource.GOOGLE_DRIVE else "Uploaded:"

            page_info = f" | PAGE_{result.page_number}" if result.page_number else ""

            formatted_chunk = f"**Document: {source_prefix} {result.document_name}{page_info}**\n\n{result.content}\n\n"
            context_parts.append(formatted_chunk)

        combined_context = "".join(context_parts)

        logger.info(f"Generated mixed context with {len(results)} chunks from both sources")
        return combined_context

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of unified search service.

        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test unified collection
            collection_health = await self._check_collection_health(self.unified_collection)

            return {
                "status": "healthy",
                "unified_collection": collection_health,
                "unified_search": True,
                "supports_both_sources": True
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "unified_search": False
            }

    async def _check_collection_health(self, collection_name: str) -> Dict[str, Any]:
        """Check health of a specific Qdrant collection."""
        try:
            # Get collection info
            collection_info = current_qdrant_client.get_collection(collection_name)

            return {
                "collection_name": collection_name,
                "exists": True,
                "point_count": collection_info.points_count if hasattr(collection_info, 'points_count') else 0,
                "status": "healthy"
            }
        except Exception as e:
            return {
                "collection_name": collection_name,
                "exists": False,
                "error": str(e),
                "status": "error"
            }

# Global instance
unified_search_service = UnifiedSearchService()