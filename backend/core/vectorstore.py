"""
VerdictFlow — Qdrant Vector Store Manager

Manages document embeddings using Qdrant with built-in FastEmbed
for CPU-local embedding generation. Supports indexing, searching,
and deletion of document chunks.
"""

import logging
import os
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger("verdictflow.vectorstore")

# Collection name for contract chunks
COLLECTION_NAME = "verdictflow_contracts"

# Embedding model — runs locally on CPU via FastEmbed
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2 output dimension


class VectorStoreManager:
    """
    Manages Qdrant vector store operations for VerdictFlow.

    Uses Qdrant's built-in FastEmbed for local CPU-based embedding
    generation — no external API calls needed for embeddings.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY") or None

        # Initialize Qdrant client
        if self.url == ":memory:":
            self.client = QdrantClient(":memory:")
        else:
            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key if self.api_key else None,
            )

        # Set the embedding model for FastEmbed
        self.client.set_model(EMBEDDING_MODEL)

        logger.info(f"🔗 Qdrant client initialized: {self.url}")

    def ensure_collection(self):
        """Create the collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"✅ Created Qdrant collection: {COLLECTION_NAME}")
        else:
            logger.info(f"✅ Qdrant collection already exists: {COLLECTION_NAME}")

    def index_document(self, doc_id: str, chunks: list) -> int:
        """
        Index document chunks into Qdrant.

        Uses FastEmbed to generate embeddings locally on CPU.
        Each chunk is stored with its text and metadata as payload.

        Args:
            doc_id: Unique document identifier
            chunks: List of TextChunk objects from the chunker

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            logger.warning(f"⚠️  No chunks to index for doc '{doc_id}'")
            return 0

        # Prepare documents and metadata for Qdrant's add method
        documents = []
        metadata_list = []

        for chunk in chunks:
            documents.append(chunk.text)
            metadata_list.append({
                "doc_id": doc_id,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "section_header": chunk.section_header,
                "char_count": chunk.char_count,
                "text": chunk.text,  # Store full text in payload for retrieval
            })

        # Use Qdrant's add method which handles embedding via FastEmbed
        self.client.add(
            collection_name=COLLECTION_NAME,
            documents=documents,
            metadata=metadata_list,
        )

        logger.info(f"📥 Indexed {len(chunks)} chunks for doc '{doc_id}'")
        return len(chunks)

    def search(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Semantic search across indexed contract chunks.

        Args:
            query: Natural language search query
            doc_id: Optional — filter results to a specific document
            top_k: Number of top results to return

        Returns:
            List of dicts with 'text', 'score', and metadata
        """
        # Build filter for document-specific search
        query_filter = None
        if doc_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id),
                    )
                ]
            )

        # Use Qdrant's query method with FastEmbed
        results = self.client.query(
            collection_name=COLLECTION_NAME,
            query_text=query,
            query_filter=query_filter,
            limit=top_k,
        )

        # Format results
        formatted = []
        for point in results:
            payload = point.metadata
            formatted.append({
                "text": payload.get("text", ""),
                "score": point.score,
                "chunk_id": payload.get("chunk_id"),
                "chunk_index": payload.get("chunk_index"),
                "page_number": payload.get("page_number"),
                "section_header": payload.get("section_header"),
                "doc_id": payload.get("doc_id"),
            })

        logger.info(f"🔍 Search '{query[:50]}...' → {len(formatted)} results (doc: {doc_id or 'all'})")
        return formatted

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete all chunks belonging to a specific document.

        Args:
            doc_id: Document ID to delete

        Returns:
            True if deletion was successful
        """
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
        )

        logger.info(f"🗑️  Deleted all chunks for doc '{doc_id}'")
        return True

    def get_collection_info(self) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(COLLECTION_NAME)
        return {
            "name": COLLECTION_NAME,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value,
        }
