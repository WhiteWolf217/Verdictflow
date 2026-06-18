/**
 * VerdictFlow — Band Agents Panel
 *
 * Shows the 6 specialized agents coordinated through Band, with a live
 * indicator once each agent has opened its own Band session for this case.
 * Self-contained: polls /cases/{id}/room and degrades gracefully if Band
 * coordination is unavailable.
 */

"use client";

import { useEffect, useState } from "react";
import { getCaseRoom, type BandRoom } from "@/lib/api";

const AGENTS = [
  { key: "intake agent", label: "Intake", desc: "Parse · classify · index", accent: "text-sky-400", dot: "bg-sky-400" },
  { key: "clause analyst", label: "Clause Analyst", desc: "Clause-by-clause risk", accent: "text-violet-400", dot: "bg-violet-400" },
  { key: "red team", label: "Red Team", desc: "Adversarial attack/defend", accent: "text-red-400", dot: "bg-red-400" },
  { key: "financial risk", label: "Financial Risk", desc: "Quantify exposure", accent: "text-amber-400", dot: "bg-amber-400" },
  { key: "compliance", label: "Compliance", desc: "GDPR · SOX · HIPAA", accent: "text-emerald-400", dot: "bg-emerald-400" },
  { key: "redline", label: "Redline", desc: "Edit suggestions", accent: "text-blue-400", dot: "bg-blue-400" },
];

export default function BandAgents({ caseId }: { caseId: string }) {
  const [room, setRoom] = useState<BandRoom | null>(null);

  useEffect(() => {
    let active = true;
    const fetchRoom = async () => {
      const r = await getCaseRoom(caseId);
      if (active) setRoom(r);
    };
    fetchRoom();
    const id = setInterval(fetchRoom, 4000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [caseId]);

  const chats = room?.agent_chats || {};
  const liveCount = AGENTS.filter((a) => chats[a.key]).length;
  const onBand = room?.mode === "band_rest";

  return (
    <div className="surface-1 p-5 mt-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <p className="metric-label">Multi-Agent Coordination</p>
          <span className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded font-mono">
            Band
          </span>
        </div>
        <span className="flex items-center gap-1.5 text-[11px] text-zinc-500">
          <span className={`status-dot ${onBand ? "status-dot-online" : ""}`} />
          {onBand ? `${liveCount}/6 agents live on Band` : "in-memory coordination"}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {AGENTS.map((a) => {
          const chatId = chats[a.key];
          const isLive = Boolean(chatId);
          return (
            <div
              key={a.key}
              className={`rounded-lg border p-3 transition-colors ${
                isLive ? "border-zinc-700/60 bg-zinc-800/20" : "border-zinc-800/40 bg-transparent"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-[12px] font-medium ${isLive ? a.accent : "text-zinc-500"}`}>
                  {a.label}
                </span>
                <span
                  className={`w-1.5 h-1.5 rounded-full ${isLive ? a.dot : "bg-zinc-700"} ${
                    isLive ? "animate-pulse" : ""
                  }`}
                />
              </div>
              <p className="text-[10px] text-zinc-600 leading-tight">{a.desc}</p>
              {isLive && (
                <p className="text-[9px] text-zinc-700 font-mono mt-1.5 truncate" title={chatId}>
                  session {chatId.slice(0, 8)}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
