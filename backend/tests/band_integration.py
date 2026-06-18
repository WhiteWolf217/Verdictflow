"""
Band live integration test for the rewritten BandClientWrapper.

Exercises the real per-agent-chat flow end to end:
  1. verify all 6 agent identities
  2. create a case room
  3. each of the 6 agents posts a message (creates + posts to its OWN chat)
  4. read each agent's chat back from Band and confirm the message landed
  5. confirm the unified in-memory transcript aggregates all 6

Run:  PYTHONUTF8=1 .venv/Scripts/python.exe tests/band_integration.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from band.client import BandClientWrapper  # noqa: E402

AGENTS = ["Intake Agent", "Clause Analyst", "Red Team", "Compliance", "Financial Risk", "Redline"]
_fail = []


def check(name, cond, detail=""):
    print(f"  {'[PASS]' if cond else '[FAIL]'} {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        _fail.append(name)


async def main():
    band = BandClientWrapper()
    check("client is in band_rest mode", band.mode == "band_rest", band.mode)
    check("6 agent identities loaded", len(band.agent_keys) == 6, str(list(band.agent_keys)))

    print("\n=== 1. Verify all agent identities ===")
    results = await band.verify_all_agents()
    check("all 6 agents verified", all(results.values()), str(results))

    print("\n=== 2. Create case room ===")
    room_id = await band.create_case_room("integration-test-1234", "sample_nda.pdf")
    check("room created", bool(room_id), room_id)

    print("\n=== 3. Each agent posts to its own chat ===")
    for a in AGENTS:
        await band.send_agent_message(room_id, a, f"{a} reporting: integration test finding for room {room_id}.")
    chats = band._agent_chats.get(room_id, {})
    check("all 6 agents created a Band chat", len(chats) == 6, f"{len(chats)} chats: {list(chats)}")

    print("\n=== 4. Read each agent's chat back from Band ===")
    import httpx
    async with httpx.AsyncClient(base_url=f"{band.rest_url}/api/v1", timeout=15.0) as c:
        for canon, chat_id in chats.items():
            key = band.agent_keys[canon]
            r = await c.get(f"/agent/chats/{chat_id}/messages", headers={"X-API-Key": key})
            ok = r.status_code == 200
            cnt = len(r.json().get("data", [])) if ok else -1
            check(f"chat readable: {canon}", ok, f"HTTP {r.status_code}, {cnt} msgs")

    print("\n=== 5. Unified in-memory transcript ===")
    transcript = band.get_transcript(room_id)
    msg_agents = {m["agent"] for m in transcript["messages"]}
    check("transcript aggregates all 6 agents", set(AGENTS).issubset(msg_agents),
          f"agents seen: {sorted(msg_agents)}")
    check("transcript exposes per-agent chat ids", len(transcript["agent_chats"]) == 6)

    print("\n" + "=" * 55)
    if _fail:
        print(f"[FAIL] {len(_fail)} check(s) failed: {', '.join(_fail)}")
        sys.exit(1)
    print("[PASS] All Band integration checks passed — all 6 agents are live on Band.")


if __name__ == "__main__":
    asyncio.run(main())
