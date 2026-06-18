"""
VerdictFlow — Tests for core infrastructure.
"""

import json
import pytest
from core.chunker import chunk_text, _is_heading
from models.audit import AuditChain


# ── Chunker Tests ────────────────────────────────────────────────────────────


class TestChunker:
    def test_basic_chunking(self):
        text = "This is a test sentence. " * 100  # ~2500 chars
        chunks = chunk_text(text, doc_id="test-doc", max_chars=500)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.doc_id == "test-doc"
            assert len(chunk.text) <= 600  # Allow some overlap overshoot

    def test_empty_text(self):
        chunks = chunk_text("", doc_id="test-doc")
        assert len(chunks) == 0

    def test_short_text(self):
        chunks = chunk_text("Short text.", doc_id="test-doc", max_chars=500)
        assert len(chunks) == 1
        assert chunks[0].text == "Short text."

    def test_heading_detection(self):
        assert _is_heading("ARTICLE 1. PURPOSE")
        assert _is_heading("SECTION 3. DEFINITIONS")
        assert _is_heading("1. Introduction")
        assert _is_heading("CONFIDENTIALITY AGREEMENT")
        assert not _is_heading("This is a regular sentence.")
        assert not _is_heading("")

    def test_chunk_metadata(self):
        text = "Test content for chunking"
        chunks = chunk_text(text, doc_id="doc-123", page_number=5)
        assert chunks[0].doc_id == "doc-123"
        assert chunks[0].page_number == 5
        assert chunks[0].chunk_index == 0


# ── Audit Trail Tests ────────────────────────────────────────────────────────


class TestAuditChain:
    def test_empty_chain(self):
        chain = AuditChain()
        is_valid, error = chain.verify_integrity()
        assert is_valid
        assert error is None
        assert len(chain) == 0

    def test_single_entry(self):
        chain = AuditChain()
        entry = chain.add_entry("test_agent", "test_action", {"key": "value"})
        assert entry.step_index == 0
        assert entry.agent_name == "test_agent"
        assert entry.previous_hash == "0" * 64  # Genesis hash

        is_valid, error = chain.verify_integrity()
        assert is_valid
        assert error is None

    def test_chain_linkage(self):
        chain = AuditChain()
        entry0 = chain.add_entry("agent_a", "action_1", {"data": 1})
        entry1 = chain.add_entry("agent_b", "action_2", {"data": 2})
        entry2 = chain.add_entry("agent_c", "action_3", {"data": 3})

        # Verify linkage
        assert entry1.previous_hash == entry0.current_hash
        assert entry2.previous_hash == entry1.current_hash

        is_valid, error = chain.verify_integrity()
        assert is_valid

    def test_tamper_detection(self):
        chain = AuditChain()
        chain.add_entry("agent_a", "action_1", {"data": 1})
        chain.add_entry("agent_b", "action_2", {"data": 2})
        chain.add_entry("agent_c", "action_3", {"data": 3})

        # Tamper with entry 1
        chain.entries[1].data_hash = "tampered_hash_value"

        is_valid, error = chain.verify_integrity()
        assert not is_valid
        assert "step 1" in error

    def test_export_json(self):
        chain = AuditChain()
        chain.add_entry("agent_a", "action_1", {"key": "val"})
        exported = chain.export_json()
        assert len(exported) == 1
        assert exported[0]["agent_name"] == "agent_a"
        assert exported[0]["action"] == "action_1"

    def test_different_data_different_hashes(self):
        chain = AuditChain()
        entry1 = chain.add_entry("agent", "action", {"data": "version_1"})

        chain2 = AuditChain()
        entry2 = chain2.add_entry("agent", "action", {"data": "version_2"})

        assert entry1.data_hash != entry2.data_hash

    def test_latest_hash(self):
        chain = AuditChain()
        assert chain.get_latest_hash() == "0" * 64

        entry = chain.add_entry("agent", "action", {})
        assert chain.get_latest_hash() == entry.current_hash
