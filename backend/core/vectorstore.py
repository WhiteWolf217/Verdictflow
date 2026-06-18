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

# Collection for the uploaded contract's own chunks (per-document RAG)
COLLECTION_NAME = "verdictflow_contracts"

# Collection for the market-standard precedent clause library. The Clause
# Analyst compares contract clauses against these to ground its findings.
PRECEDENTS_COLLECTION = "verdictflow_precedents"

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

    def _existing_collections(self) -> list[str]:
        return [c.name for c in self.client.get_collections().collections]

    def ensure_collection(self):
        """
        Create the contract-chunks collection if it doesn't exist.

        IMPORTANT: the collection must be configured with FastEmbed's *named*
        vector params (via ``get_fastembed_vector_params``), because
        ``client.add()`` / ``client.query()`` upsert and search a named vector.
        Creating a plain unnamed ``VectorParams`` here would make every
        ``.add()`` fail with "vector name not found".
        """
        if COLLECTION_NAME not in self._existing_collections():
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=self.client.get_fastembed_vector_params(),
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

    # ── Precedent Library ────────────────────────────────────────────────────

    def seed_precedents(self) -> int:
        """
        Seed the market-standard precedent clause library (idempotent).

        Creates the precedents collection if needed and loads the baseline
        clause templates the first time. Subsequent calls are no-ops once the
        library is populated. Returns the number of precedents in the library.
        """
        if PRECEDENTS_COLLECTION not in self._existing_collections():
            self.client.create_collection(
                collection_name=PRECEDENTS_COLLECTION,
                vectors_config=self.client.get_fastembed_vector_params(),
            )

        # Already seeded? (count > 0 → skip)
        try:
            count = self.client.count(PRECEDENTS_COLLECTION).count
        except Exception:
            count = 0

        if count and count >= len(PRECEDENT_LIBRARY):
            logger.info(f"✅ Precedent library already loaded: {count} clauses")
            return count

        documents = [p["standard_text"] for p in PRECEDENT_LIBRARY]
        metadata = [
            {
                "clause_type": p["clause_type"],
                "standard_text": p["standard_text"],
                "risk_notes": p["risk_notes"],
                "text": p["standard_text"],
            }
            for p in PRECEDENT_LIBRARY
        ]
        self.client.add(
            collection_name=PRECEDENTS_COLLECTION,
            documents=documents,
            metadata=metadata,
        )
        logger.info(f"📚 Baseline library loaded: {len(PRECEDENT_LIBRARY)} clauses")
        return len(PRECEDENT_LIBRARY)

    def search_precedents(self, query: str, top_k: int = 1) -> list[dict]:
        """
        Find the closest market-standard precedent clause(s) for a query.

        Returns a list of dicts with 'clause_type', 'standard_text',
        'risk_notes', and 'score'. Returns [] if the library is unavailable.
        """
        try:
            results = self.client.query(
                collection_name=PRECEDENTS_COLLECTION,
                query_text=query,
                limit=top_k,
            )
        except Exception as e:
            logger.warning(f"⚠️  Precedent search failed: {e}")
            return []

        out = []
        for point in results:
            payload = point.metadata
            out.append({
                "clause_type": payload.get("clause_type", ""),
                "standard_text": payload.get("standard_text", payload.get("text", "")),
                "risk_notes": payload.get("risk_notes", ""),
                "score": point.score,
            })
        return out


# ── Baseline Precedent Library ───────────────────────────────────────────────
# Market-standard clause templates the Clause Analyst compares against. Each
# entry pairs a fair, standard clause with notes on what makes a variant risky.

PRECEDENT_LIBRARY: list[dict] = [
    {
        "clause_type": "confidentiality_mutual",
        "standard_text": (
            "Each party shall protect the other's Confidential Information using "
            "the same degree of care it uses for its own, and in no event less than "
            "reasonable care. Confidentiality obligations survive for three (3) years "
            "after termination. Confidential Information excludes information that is "
            "or becomes public through no fault of the receiving party, was lawfully "
            "known prior to disclosure, or is independently developed."
        ),
        "risk_notes": (
            "Standard mutual NDA term is 2–5 years with public-information carve-outs. "
            "Perpetual/irrevocable confidentiality with no sunset and no carve-out for "
            "public information is HIGH risk and non-standard."
        ),
    },
    {
        "clause_type": "confidentiality_one_way",
        "standard_text": (
            "The Receiving Party shall hold the Disclosing Party's Confidential "
            "Information in confidence and use it solely to evaluate the proposed "
            "relationship, for a period of two (2) years from disclosure."
        ),
        "risk_notes": "One-way NDAs are common; durations beyond 5 years or with no carve-outs are negotiable.",
    },
    {
        "clause_type": "limitation_of_liability",
        "standard_text": (
            "Except for breaches of confidentiality, indemnification obligations, or "
            "gross negligence, neither party's aggregate liability shall exceed the "
            "fees paid in the twelve (12) months preceding the claim. Neither party is "
            "liable for indirect, incidental, or consequential damages."
        ),
        "risk_notes": (
            "Market caps are typically 12 months of fees. A nominal cap (e.g. $100) or "
            "total absence of any liability cap is HIGH risk."
        ),
    },
    {
        "clause_type": "indemnification_standard",
        "standard_text": (
            "Each party shall indemnify the other against third-party claims arising "
            "from its breach of this Agreement or its negligence or willful misconduct, "
            "subject to prompt notice and the indemnifying party's control of the defense."
        ),
        "risk_notes": "Mutual, claim-scoped indemnification is standard.",
    },
    {
        "clause_type": "indemnification_broad",
        "standard_text": (
            "The Customer shall indemnify, defend, and hold harmless the Vendor from any "
            "and all claims, losses, and liabilities of any kind whatsoever arising in "
            "connection with the Agreement, regardless of cause."
        ),
        "risk_notes": (
            "One-sided, uncapped 'any and all claims regardless of cause' indemnities "
            "are HIGH risk and deviate sharply from mutual market standard."
        ),
    },
    {
        "clause_type": "payment_terms_net30",
        "standard_text": "Undisputed invoices are payable within thirty (30) days of receipt (Net-30).",
        "risk_notes": "Net-30 is standard. Net-60/90 shifts working-capital burden; below Net-15 is aggressive.",
    },
    {
        "clause_type": "auto_renewal",
        "standard_text": (
            "This Agreement renews for successive twelve (12) month terms unless either "
            "party gives written notice of non-renewal at least sixty (60) days before "
            "the end of the then-current term."
        ),
        "risk_notes": (
            "Standard renewal notice windows are 30–90 days. Auto-renewal with a very "
            "short cancellation window (e.g. 7 days) or no notice provision is risky."
        ),
    },
    {
        "clause_type": "ip_assignment_employer",
        "standard_text": (
            "Work product created by Employee within the scope of employment and using "
            "Company resources is assigned to the Company. Pre-existing IP and inventions "
            "developed entirely on the Employee's own time without Company resources are excluded."
        ),
        "risk_notes": "Scope-limited assignment with pre-existing-IP carve-out is standard.",
    },
    {
        "clause_type": "ip_assignment_overbroad",
        "standard_text": (
            "All work product and any inventions conceived during the term, whether or not "
            "related to the Company's business, are the sole and exclusive property of the Vendor."
        ),
        "risk_notes": (
            "Assigning ALL work product (including unrelated/pre-existing IP) to one party "
            "is HIGH risk and exceeds market norms."
        ),
    },
    {
        "clause_type": "gdpr_dpa",
        "standard_text": (
            "Where the Processor processes personal data on behalf of the Controller, the "
            "parties shall enter a Data Processing Agreement compliant with GDPR Article 28, "
            "specifying processing purposes, sub-processor controls, security measures, and "
            "data-deletion obligations on termination."
        ),
        "risk_notes": (
            "Contracts involving personal data processing must reference a GDPR-compliant DPA "
            "and data deletion on termination. Their absence is a compliance gap."
        ),
    },
    {
        "clause_type": "non_compete",
        "standard_text": (
            "For twelve (12) months after termination, Employee shall not engage in a "
            "directly competing business within the geographic territory where the Company "
            "actively operates, limited to substantially similar services."
        ),
        "risk_notes": (
            "Enforceable non-competes are narrow in time (≤1–2 yrs), geography, and scope. "
            "'2 years globally in any industry' is unreasonable and likely unenforceable — HIGH risk."
        ),
    },
    {
        "clause_type": "non_solicitation",
        "standard_text": (
            "For twelve (12) months after termination, neither party shall solicit for "
            "employment the other's employees with whom it had material contact, excluding "
            "responses to general public job postings."
        ),
        "risk_notes": "12-month, contact-scoped non-solicitation is standard.",
    },
    {
        "clause_type": "governing_law",
        "standard_text": (
            "This Agreement is governed by the laws of the State of Delaware, without regard "
            "to its conflict-of-laws principles, and the parties consent to the exclusive "
            "jurisdiction of the state and federal courts located therein."
        ),
        "risk_notes": (
            "Governing law should name a specific, neutral jurisdiction. A floating clause "
            "(e.g. 'the disclosing party's jurisdiction') with no named state is risky."
        ),
    },
    {
        "clause_type": "service_level_agreement",
        "standard_text": (
            "Vendor will maintain 99.9% monthly uptime, measured monthly, with service "
            "credits of 5–25% of monthly fees for defined breaches, excluding scheduled maintenance."
        ),
        "risk_notes": (
            "Enforceable SLAs are quantified with remedies. 'Commercially reasonable efforts' "
            "with no metric or credit is unenforceable and risky."
        ),
    },
    {
        "clause_type": "auto_renewal_without_notice",
        "standard_text": (
            "This Agreement shall automatically renew for successive one (1) year terms. "
            "Either party may cancel by providing written notice at least seven (7) days "
            "before the end of the then-current term. Failure to cancel shall constitute "
            "acceptance of the renewal and all applicable fees."
        ),
        "risk_notes": (
            "A 7-day cancellation window on a yearly auto-renewal is extremely aggressive "
            "and easy to miss, effectively locking the party in. Standard practice is 30–90 "
            "days' notice. This is HIGH risk and often negotiable."
        ),
    },
    {
        "clause_type": "payment_terms_net60",
        "standard_text": (
            "All undisputed invoices shall be payable within sixty (60) days of receipt "
            "(Net-60). Late payments shall bear interest at the lesser of 1.5% per month "
            "or the maximum rate permitted by applicable law."
        ),
        "risk_notes": (
            "Net-60 shifts working-capital burden to the vendor/supplier. Standard B2B terms "
            "are Net-30. Net-60 or longer is negotiable and may signal cash-flow risk on the "
            "paying party's side."
        ),
    },
]
