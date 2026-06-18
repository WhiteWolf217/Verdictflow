/**
 * VerdictFlow — Live Boardroom Sidebar
 * 
 * Always-visible sidebar showing agents "talking" in real-time during pipeline
 * processing. When analysis completes, auto-triggers the cross-examination debate.
 * This is the headline feature — judges see agents reasoning against each other live.
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { getAgentDebate, type DebateRound } from "@/lib/api";

/* ── Agent visual identities ─────────────────────────────────────── */

const AGENTS: Record<string, { color: string; bg: string; glow: string; initials: string; emoji: string }> = {
  "Intake Agent":     { color: "text-cyan-400",    bg: "bg-cyan-500/20",    glow: "shadow-cyan-500/20",    initials: "IA", emoji: "📋" },
  "Clause Analyst":   { color: "text-violet-400",  bg: "bg-violet-500/20",  glow: "shadow-violet-500/20",  initials: "CA", emoji: "🔍" },
  "Red Team":         { color: "text-red-400",     bg: "bg-red-500/20",     glow: "shadow-red-500/20",     initials: "RT", emoji: "🗡️" },
  "Financial Risk":   { color: "text-amber-400",   bg: "bg-amber-500/20",   glow: "shadow-amber-500/20",   initials: "FR", emoji: "💰" },
  "Compliance":       { color: "text-emerald-400", bg: "bg-emerald-500/20", glow: "shadow-emerald-500/20", initials: "CO", emoji: "⚖️" },
  "Redline":          { color: "text-blue-400",    bg: "bg-blue-500/20",    glow: "shadow-blue-500/20",    initials: "RL", emoji: "✏️" },
  "Adjudicator":      { color: "text-indigo-400",  bg: "bg-indigo-500/20",  glow: "shadow-indigo-500/20",  initials: "AJ", emoji: "⚡" },
  "Orchestrator":     { color: "text-zinc-400",    bg: "bg-zinc-500/20",    glow: "shadow-zinc-500/20",    initials: "OR", emoji: "🎯" },
};

const STANCE_BADGE: Record<string, string> = {
  challenge: "bg-red-400/15 text-red-400 border border-red-400/20",
  defend:    "bg-blue-400/15 text-blue-400 border border-blue-400/20",
  concede:   "bg-amber-400/15 text-amber-400 border border-amber-400/20",
  rule:      "bg-indigo-400/15 text-indigo-400 border border-indigo-400/20",
  report:    "bg-zinc-400/15 text-zinc-400 border border-zinc-400/20",
};

/* ── Types ───────────────────────────────────────────────────────── */

interface LiveMessage {
  id: string;
  speaker: string;
  message: string;
  stance: string;
  timestamp: number;
}

interface SSEEvent {
  event_type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

interface Props {
  caseId: string;
  events: SSEEvent[];
  status: string;
}

/* ── Component ───────────────────────────────────────────────────── */

export default function LiveBoardroom({ caseId, events, status }: Props) {
  const [messages, setMessages] = useState<LiveMessage[]>([]);
  const [debateRounds, setDebateRounds] = useState<DebateRound[]>([]);
  const [debateRevealed, setDebateRevealed] = useState(0);
  const [isDebating, setIsDebating] = useState(false);
  const [debateTriggered, setDebateTriggered] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevEventCountRef = useRef(0);

  // Convert SSE events to chat messages
  useEffect(() => {
    if (events.length <= prevEventCountRef.current) return;
    prevEventCountRef.current = events.length;

    const newMessages: LiveMessage[] = [];
    events.forEach((evt, idx) => {
      const d = evt.data;
      const id = `sse-${idx}`;
      
      if (evt.event_type === "agent_started") {
        const agentName = agentIdToName(d.agent as string);
        newMessages.push({
          id, speaker: agentName,
          message: `Starting analysis...`,
          stance: "report", timestamp: Date.now(),
        });
      } else if (evt.event_type === "agent_completed") {
        const agentName = agentIdToName(d.agent as string);
        newMessages.push({
          id, speaker: agentName,
          message: d.message as string || `Completed with ${d.count} findings`,
          stance: "report", timestamp: Date.now(),
        });
      } else if (evt.event_type === "stage_started") {
        newMessages.push({
          id, speaker: "Orchestrator",
          message: `${d.stage_name || d.stage}: ${d.message || "Starting..."}`,
          stance: "report", timestamp: Date.now(),
        });
      } else if (evt.event_type === "gate_requested") {
        newMessages.push({
          id, speaker: "Orchestrator",
          message: `All agents have reported. Requesting human review. Verdict: ${d.recommendation || "pending"}`,
          stance: "report", timestamp: Date.now(),
        });
      }
    });

    if (newMessages.length > 0) {
      setMessages(prev => {
        const existingIds = new Set(prev.map(m => m.id));
        const unique = newMessages.filter(m => !existingIds.has(m.id));
        return [...prev, ...unique];
      });
    }
  }, [events]);

  // Auto-trigger debate when pipeline completes
  useEffect(() => {
    if ((status === "awaiting_review" || status === "approved" || status === "rejected") && !debateTriggered && messages.length > 0) {
      setDebateTriggered(true);
      runDebate();
    }
  }, [status, messages.length, debateTriggered]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, debateRevealed]);

  const runDebate = async () => {
    setIsDebating(true);
    // Add "convening" message
    setMessages(prev => [...prev, {
      id: `debate-start`,
      speaker: "Orchestrator",
      message: "⚡ Convening the Boardroom — agents will now cross-examine each other's findings...",
      stance: "report",
      timestamp: Date.now(),
    }]);

    try {
      const data = await getAgentDebate(caseId);
      setDebateRounds(data);
      // Reveal debate messages one-by-one for live feel
      data.forEach((_, i) => {
        setTimeout(() => setDebateRevealed(i + 1), (i + 1) * 900);
      });
    } catch {
      setMessages(prev => [...prev, {
        id: `debate-error`,
        speaker: "Orchestrator",
        message: "Could not convene boardroom debate. Try again later.",
        stance: "report",
        timestamp: Date.now(),
      }]);
    }
    setIsDebating(false);
  };

  const allMessages = [
    ...messages,
    ...debateRounds.slice(0, debateRevealed).map((r, i) => ({
      id: `debate-${i}`,
      speaker: r.speaker,
      message: r.message,
      stance: r.stance,
      timestamp: Date.now() + i,
    })),
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800/80 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[13px] font-semibold text-zinc-200">Agent Boardroom</span>
        </div>
        {(status === "awaiting_review" || status === "approved") && !isDebating && (
          <button
            onClick={() => { setDebateRounds([]); setDebateRevealed(0); runDebate(); }}
            className="text-[10px] px-2 py-1 rounded bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 transition-colors"
          >
            Re-debate
          </button>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2 scrollbar-thin">
        {allMessages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center mb-3">
              <span className="text-lg">🏛️</span>
            </div>
            <p className="text-[12px] text-zinc-600 max-w-[200px]">
              Agents will appear here as they analyze the contract and debate findings.
            </p>
          </div>
        )}

        {allMessages.map((msg) => {
          const agent = AGENTS[msg.speaker] || AGENTS["Orchestrator"];
          const isDebateMsg = msg.id.startsWith("debate-") && !msg.id.startsWith("debate-start");
          const isRuling = msg.stance === "rule";

          return (
            <div
              key={msg.id}
              className={`animate-slide-up ${
                isRuling ? "border-l-2 border-l-indigo-500 pl-2" : ""
              } ${isDebateMsg ? "ml-1" : ""}`}
            >
              <div className="flex items-start gap-2">
                {/* Avatar */}
                <div className={`w-6 h-6 rounded-md ${agent.bg} flex items-center justify-center shrink-0 mt-0.5 shadow-sm ${agent.glow}`}>
                  <span className={`text-[8px] font-bold ${agent.color}`}>{agent.initials}</span>
                </div>

                <div className="min-w-0 flex-1">
                  {/* Speaker + stance */}
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className={`text-[11px] font-semibold ${agent.color}`}>{msg.speaker}</span>
                    {isDebateMsg && msg.stance && (
                      <span className={`text-[8px] px-1.5 py-0.5 rounded-full font-medium ${STANCE_BADGE[msg.stance] || STANCE_BADGE.report}`}>
                        {msg.stance}
                      </span>
                    )}
                  </div>

                  {/* Message */}
                  <p className={`text-[11px] leading-relaxed ${
                    isRuling ? "text-indigo-300 font-medium" : "text-zinc-400"
                  }`}>
                    {msg.message}
                  </p>
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {(isDebating || (status === "processing" && messages.length > 0)) && (
          <div className="flex items-center gap-1.5 pl-8 pt-1">
            <span className="w-1 h-1 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0s" }} />
            <span className="w-1 h-1 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0.15s" }} />
            <span className="w-1 h-1 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0.3s" }} />
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Helpers ──────────────────────────────────────────────────────── */

function agentIdToName(id: string): string {
  const map: Record<string, string> = {
    intake_agent: "Intake Agent",
    clause_analyst: "Clause Analyst",
    red_team: "Red Team",
    financial_risk: "Financial Risk",
    compliance: "Compliance",
    redline: "Redline",
    adjudicator: "Adjudicator",
  };
  return map[id] || id;
}
