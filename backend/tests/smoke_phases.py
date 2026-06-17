"""
VerdictFlow — Deterministic smoke test for Phases 1 & 2.

Exercises everything that does NOT require an external LLM API key:
  - Phase 1: .txt / parsing, chunking, vector store + precedent library (RAG)
  - Phase 2: in-memory Band case room transcript
  - Audit hash chain + tamper detection

Run from the backend/ directory with the venv Python:
    .venv\\Scripts\\python.exe tests\\smoke_phases.py

Uses an in-memory Qdrant (":memory:") so no Docker is needed. FastEmbed will
download the MiniLM model on first run (~90 MB), then cache it.
"""

import os
import sys
import tempfile

# Ensure backend/ is importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL = "[PASS]", "[FAIL]"
_failures = []


def check(name: str, cond: bool, detail: str = ""):
    mark = PASS if cond else FAIL
    print(f"  {mark} {name}" + (f" - {detail}" if detail else ""))
    if not cond:
        _failures.append(name)


SAMPLE_NDA = """MUTUAL NON-DISCLOSURE AGREEMENT

1. CONFIDENTIAL INFORMATION
The parties agree that all information disclosed in any form, whether marked or
not, constitutes Confidential Information. This obligation is PERPETUAL AND
IRREVOCABLE and shall survive termination indefinitely with no sunset.

2. NON-COMPETE
For a period of 2 years globally in any industry, the Receiving Party shall not
engage in any business activity.

3. AUTO-RENEWAL
This Agreement renews automatically unless cancelled with 7 days written notice.

4. GOVERNING LAW
This Agreement is governed by the laws of the disclosing party's jurisdiction.

5. LIABILITY
The Receiving Party accepts unlimited liability for any breach.
"""


def main():
    print("\n=== Phase 1: Parser (.txt) ===")
    from core.parser import parse_contract, SUPPORTED_EXTENSIONS

    check(".txt is a supported extension", ".txt" in SUPPORTED_EXTENSIONS)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_NDA)
        txt_path = f.name

    parsed = parse_contract(txt_path, "sample_nda.txt")
    check("parsed .txt has text", len(parsed.raw_text) > 200, f"{parsed.total_chars} chars")
    check("parser detected headings", any(p.headings for p in parsed.pages),
          f"{sum(len(p.headings) for p in parsed.pages)} headings")
    check("file_type == txt", parsed.file_type == "txt")

    print("\n=== Phase 1: Chunker ===")
    from core.chunker import chunk_document
    chunks = chunk_document(parsed)
    check("produced >= 1 chunk", len(chunks) >= 1, f"{len(chunks)} chunks")
    check("chunks carry doc_id", all(c.doc_id == parsed.doc_id for c in chunks))

    print("\n=== Phase 1: Vector store + precedent library (in-memory Qdrant) ===")
    from core.vectorstore import VectorStoreManager, PRECEDENT_LIBRARY
    vs = VectorStoreManager(url=":memory:")
    vs.ensure_collection()
    n_indexed = vs.index_document(parsed.doc_id, chunks)
    check("indexed chunks into Qdrant", n_indexed == len(chunks), f"{n_indexed} indexed")

    results = vs.search("non-compete restriction", doc_id=parsed.doc_id, top_k=3)
    check("RAG search returns hits", len(results) >= 1, f"{len(results)} hits")

    seeded = vs.seed_precedents()
    check("precedent library seeded", seeded == len(PRECEDENT_LIBRARY), f"{seeded} clauses")
    # idempotent
    seeded2 = vs.seed_precedents()
    check("precedent seeding is idempotent", seeded2 == seeded)

    prec = vs.search_precedents("non-compete clause", top_k=1)
    check("precedent search returns a standard clause", len(prec) == 1,
          prec[0]["clause_type"] if prec else "none")
    check("precedent has risk_notes", bool(prec and prec[0].get("risk_notes")))

    print("\n=== Phase 2: Band in-memory case room ===")
    import asyncio
    from band.client import BandClientWrapper

    band = BandClientWrapper()
    check("band mode is in_memory (no SDK)", band.mode == "in_memory", band.mode)

    async def band_flow():
        room_id = await band.create_case_room("case-1234abcd", "sample_nda.txt")
        await band.send_agent_message(room_id, "Legal Analyst", "Found a perpetual confidentiality clause.")
        await band.send_event(room_id, "clause_analysis_complete", {"findings": 3})
        history = await band.get_room_history(room_id)
        transcript = band.get_transcript(room_id)
        return room_id, history, transcript

    room_id, history, transcript = asyncio.run(band_flow())
    check("room created", bool(room_id), room_id)
    # System opening message + the agent message
    check("transcript stores messages", len(history) >= 2, f"{len(history)} messages")
    check("transcript stores events", len(transcript["events"]) >= 1,
          f"{len(transcript['events'])} events")
    check("transcript exposes url", transcript["url"].endswith(f"/rooms/{room_id}"))

    print("\n=== Audit hash chain ===")
    from models.audit import AuditChain
    chain = AuditChain()
    chain.add_entry("intake", "intake_complete", {"pages": 1}, summary="parsed")
    chain.add_entry("clause", "clause_complete", [{"risk": "high"}], summary="1 finding")
    valid, err = chain.verify_integrity()
    check("fresh chain verifies", valid, err or "")
    # Tamper with a HASHED field (action) and re-verify — must be detected.
    if chain.entries:
        chain.entries[0].action = "TAMPERED"
        bad_valid, bad_err = chain.verify_integrity()
        check("tampering is detected", not bad_valid, bad_err or "")

    print("\n" + "=" * 50)
    if _failures:
        print(f"{FAIL} {len(_failures)} check(s) FAILED: {', '.join(_failures)}")
        sys.exit(1)
    print(f"{PASS} All Phase 1 & 2 smoke checks passed.")


if __name__ == "__main__":
    main()
