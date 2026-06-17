"""
VerdictFlow — Contract Text Chunker

Recursive text chunking with overlap, structure-aware splitting,
and metadata tagging for Qdrant indexing.
"""

import logging
import re
import uuid
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("verdictflow.chunker")


# ── Data Models ──────────────────────────────────────────────────────────────


class TextChunk(BaseModel):
    """A single chunk of contract text with metadata."""

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    chunk_index: int
    text: str
    char_count: int
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


# ── Heading Detection ────────────────────────────────────────────────────────

# Common contract heading patterns
HEADING_PATTERNS = [
    r"^(?:ARTICLE|SECTION|CLAUSE)\s+\d+",  # ARTICLE 1, SECTION 2, CLAUSE 3
    r"^\d+\.\s+[A-Z]",                      # 1. Title
    r"^\d+\.\d+\s+",                         # 1.1 Subsection
    r"^[IVXLC]+\.\s+",                       # I. Roman numeral
    r"^[A-Z][A-Z\s]{3,}$",                   # ALL CAPS HEADINGS
]


def _is_heading(line: str) -> bool:
    """Check if a line looks like a contract section heading."""
    stripped = line.strip()
    if not stripped:
        return False
    for pattern in HEADING_PATTERNS:
        if re.match(pattern, stripped):
            return True
    return False


def _extract_section_header(text: str) -> Optional[str]:
    """Extract the first heading from a text block."""
    for line in text.split("\n"):
        if _is_heading(line):
            return line.strip()
    return None


# ── Chunking Logic ───────────────────────────────────────────────────────────


def _split_by_structure(text: str) -> list[str]:
    """
    Split text at structural boundaries (headings, section breaks).
    Falls back to paragraph-level splits.
    """
    sections: list[str] = []
    current_section: list[str] = []

    for line in text.split("\n"):
        if _is_heading(line) and current_section:
            sections.append("\n".join(current_section))
            current_section = []
        current_section.append(line)

    if current_section:
        sections.append("\n".join(current_section))

    return sections


def _recursive_split(
    text: str,
    max_chars: int,
    separators: list[str],
) -> list[str]:
    """
    Recursively split text using a hierarchy of separators.
    Tries the most meaningful separator first (\n\n), then falls back
    to less meaningful ones (\n, ". ", " ").
    """
    if len(text) <= max_chars:
        return [text]

    if not separators:
        # Hard split at max_chars if no separators work
        chunks = []
        for i in range(0, len(text), max_chars):
            chunks.append(text[i : i + max_chars])
        return chunks

    sep = separators[0]
    remaining_seps = separators[1:]
    parts = text.split(sep)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for part in parts:
        part_len = len(part) + len(sep)

        if current_len + part_len > max_chars and current_chunk:
            chunk_text = sep.join(current_chunk)
            if len(chunk_text) > max_chars:
                # Recursively split oversized chunk with finer separators
                chunks.extend(_recursive_split(chunk_text, max_chars, remaining_seps))
            else:
                chunks.append(chunk_text)
            current_chunk = []
            current_len = 0

        current_chunk.append(part)
        current_len += part_len

    if current_chunk:
        chunk_text = sep.join(current_chunk)
        if len(chunk_text) > max_chars:
            chunks.extend(_recursive_split(chunk_text, max_chars, remaining_seps))
        else:
            chunks.append(chunk_text)

    return chunks


def chunk_text(
    text: str,
    doc_id: str,
    max_chars: int = 1500,  # ~375 tokens at 4 chars/token → ~512 tokens with headroom
    overlap_ratio: float = 0.1,
    page_number: Optional[int] = None,
) -> list[TextChunk]:
    """
    Chunk a text string into overlapping segments.

    Strategy:
    1. First, try structure-aware splitting (by headings)
    2. Then, recursively split oversized sections using paragraph/sentence/word boundaries
    3. Apply overlap between consecutive chunks

    Args:
        text: The raw text to chunk
        doc_id: Document ID for tagging
        max_chars: Maximum characters per chunk (~512 tokens)
        overlap_ratio: Fraction of chunk to overlap (10%)
        page_number: Optional page number for metadata

    Returns:
        List of TextChunk objects with metadata
    """
    if not text.strip():
        return []

    # Step 1: Structure-aware splitting
    sections = _split_by_structure(text)

    # Step 2: Recursive splitting of oversized sections
    separators = ["\n\n", "\n", ". ", " "]
    raw_chunks: list[str] = []
    for section in sections:
        if len(section) > max_chars:
            raw_chunks.extend(_recursive_split(section, max_chars, separators))
        else:
            raw_chunks.append(section)

    # Step 3: Apply overlap
    overlap_chars = int(max_chars * overlap_ratio)
    final_chunks: list[str] = []

    for i, chunk in enumerate(raw_chunks):
        if i > 0 and overlap_chars > 0:
            # Prepend overlap from the end of the previous chunk
            prev_text = raw_chunks[i - 1]
            overlap_text = prev_text[-overlap_chars:]
            chunk = overlap_text + " " + chunk

        final_chunks.append(chunk.strip())

    # Step 4: Build TextChunk objects
    result: list[TextChunk] = []
    for idx, chunk_text_str in enumerate(final_chunks):
        if not chunk_text_str:
            continue

        result.append(TextChunk(
            doc_id=doc_id,
            chunk_index=idx,
            text=chunk_text_str,
            char_count=len(chunk_text_str),
            page_number=page_number,
            section_header=_extract_section_header(chunk_text_str),
        ))

    logger.info(f"📦 Chunked doc '{doc_id}': {len(result)} chunks (max {max_chars} chars, {overlap_ratio:.0%} overlap)")
    return result


def chunk_document(parsed_doc, max_chars: int = 1500, overlap_ratio: float = 0.1) -> list[TextChunk]:
    """
    Chunk a ParsedDocument into overlapping segments.

    Processes each page separately to maintain page-level metadata,
    then merges all chunks with global indexing.

    Args:
        parsed_doc: A ParsedDocument from the parser module
        max_chars: Maximum characters per chunk
        overlap_ratio: Fraction overlap between chunks

    Returns:
        List of TextChunk objects spanning the entire document
    """
    all_chunks: list[TextChunk] = []
    global_index = 0

    for page in parsed_doc.pages:
        page_chunks = chunk_text(
            text=page.text,
            doc_id=parsed_doc.doc_id,
            max_chars=max_chars,
            overlap_ratio=overlap_ratio,
            page_number=page.page_number,
        )

        # Re-index globally
        for chunk in page_chunks:
            chunk.chunk_index = global_index
            global_index += 1

        all_chunks.extend(page_chunks)

    logger.info(
        f"📦 Document '{parsed_doc.filename}' chunked: "
        f"{len(all_chunks)} total chunks across {parsed_doc.page_count} pages"
    )
    return all_chunks
