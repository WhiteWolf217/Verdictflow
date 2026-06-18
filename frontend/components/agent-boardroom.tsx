/**
 * VerdictFlow — Agent Boardroom
 * Visualizes the multi-agent cross-examination: specialist agents challenge,
 * defend, and the Adjudicator rules. Showcases genuine multi-agent reasoning.
 */

"use client";

import { useState } from "react";
import { getAgentDebate, type DebateRound } from "@/lib/api";

const SPEAKER_STYLE: Record<string, { color: string; bg: string; initials: string }> = {
  "Clause Analyst": { color: "text-violet-400", bg: "bg-violet-500/20", initials: "CA" },
  "Red Team": { color: "text-red-400", bg: "bg-red-500/20", initials: "RT" },
  "Compliance": { color: "text-emerald-400", bg: "bg-emerald-500/20", initials: "CO" },
  "Adjudicator": { color: "text-indigo-400", bg: "bg-indigo-500/20", initials: "AJ" },
};

const STANCE_BADGE: Record<string, string> = {
  challenge: "bg-red-400/10 text-red-400",
  defend: "bg-blue-400/10 text-blue-400",
  concede: "bg-amber-400/10 text-amber-400",
  rule: "bg-indigo-400/10 text-indigo-400",
};

export default function AgentBoardroom({ caseId }: { caseId: string }) {
  const [rounds, setRounds] = useState<DebateRound[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [revealed, setRevealed] = useState(0);

  const run = async () => {
    setIsLoading(true);
    setRounds([]);
    setRevealed(0);
    try {
      const data = await getAgentDebate(caseId);
      setRounds(data);
      // Reveal messages one-by-one for a "live debate" feel.
      data.forEach((_, i) => setTimeout(() => setRevealed(i + 1), i * 700));
    } catch {
      setRounds([]);
    }
    setIsLoading(false);
  };

  return (
    <div className="space-y-4">
      <div className="surface-1 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[14px] font-semibold text-zinc-200">Agent Boardroom</p>
            <p className="text-[12px] text-zinc-500 mt-0.5">
              Watch the agents cross-examine each other&rsquo;s findings and reach consensus.
            </p>
          </div>
          <button onClick={run} disabled={isLoading} className="btn-primary whitespace-nowrap">
            {isLoading ? "Convening…" : rounds.length ? "Re-run Debate" : "Convene Boardroom"}
          </button>
        </div>
      </div>

      {rounds.length > 0 && (
        <div className="space-y-3">
          {rounds.slice(0, revealed).map((r, i) => {
            const s = SPEAKER_STYLE[r.speaker] || SPEAKER_STYLE["Adjudicator"];
            const isRuling = r.stance === "rule";
            return (
              <div
                key={i}
                className={`surface-1 p-4 flex items-start gap-3 animate-slide-up ${
                  isRuling ? "border border-indigo-500/30" : ""
                }`}
              >
                <div className={`w-8 h-8 rounded-lg ${s.bg} flex items-center justify-center shrink-0`}>
                  <span className={`text-[10px] font-bold ${s.color}`}>{s.initials}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[12px] font-semibold ${s.color}`}>{r.speaker}</span>
                    <span className={`badge ${STANCE_BADGE[r.stance] || "bg-zinc-400/10 text-zinc-400"}`}>
                      {r.stance}
                    </span>
                  </div>
                  <p className="text-[12px] text-zinc-300 leading-relaxed">{r.message}</p>
                </div>
              </div>
            );
          })}
          {revealed < rounds.length && (
            <div className="flex items-center gap-2 pl-4 text-zinc-600">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0.15s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0.3s" }} />
            </div>
          )}
        </div>
      )}

      {!isLoading && rounds.length === 0 && (
        <div className="surface-1 py-12 text-center">
          <p className="text-[12px] text-zinc-600">Convene the boardroom to see the agents debate the findings.</p>
        </div>
      )}
    </div>
  );
}
