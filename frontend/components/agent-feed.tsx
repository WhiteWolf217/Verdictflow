/**
 * VerdictFlow — Live Agent Feed
 * Real-time activity feed showing agent work as it happens.
 * Chat-style with agent avatars, messages, and timestamps.
 */

"use client";

import { useEffect, useRef } from "react";
import { SSEEvent } from "@/lib/use-sse";

interface AgentFeedProps {
  events: SSEEvent[];
  isConnected: boolean;
}

const AGENT_CONFIG: Record<string, { color: string; bg: string; initials: string }> = {
  intake:          { color: "text-blue-400",    bg: "bg-blue-500/20",    initials: "IN" },
  clause_analyst:  { color: "text-violet-400",  bg: "bg-violet-500/20",  initials: "CA" },
  red_team:        { color: "text-red-400",     bg: "bg-red-500/20",     initials: "RT" },
  financial_risk:  { color: "text-amber-400",   bg: "bg-amber-500/20",   initials: "FR" },
  compliance:      { color: "text-emerald-400", bg: "bg-emerald-500/20", initials: "CO" },
  redline:         { color: "text-cyan-400",    bg: "bg-cyan-500/20",    initials: "RL" },
  adjudicator:     { color: "text-indigo-400",  bg: "bg-indigo-500/20",  initials: "AJ" },
  orchestrator:    { color: "text-zinc-400",    bg: "bg-zinc-500/20",    initials: "OR" },
};

const AGENT_NAMES: Record<string, string> = {
  intake: "Intake Agent",
  clause_analyst: "Clause Analyst",
  red_team: "Red Team Agent",
  financial_risk: "Financial Risk Agent",
  compliance: "Compliance Agent",
  redline: "Redline Agent",
  adjudicator: "Adjudicator",
  orchestrator: "Orchestrator",
};

function formatEvent(event: SSEEvent): { agent: string; message: string; type: "info" | "success" | "working" | "alert" } | null {
  const agent = (event.data?.agent as string) || (event.data?.stage as string) || "orchestrator";
  const msg = event.data?.message as string;

  switch (event.event_type) {
    case "agent_started":
      return { agent, message: msg || `Starting analysis...`, type: "working" };
    case "agent_completed":
      return { agent, message: msg || `Analysis complete`, type: "success" };
    case "stage_started":
      return { agent, message: msg || `Stage initiated`, type: "info" };
    case "gate_requested":
      return { agent: "orchestrator", message: "All agents finished. Awaiting human review.", type: "alert" };
    case "case_finalized":
      return { agent: "orchestrator", message: "Case finalized. Audit report ready.", type: "success" };
    case "case_error":
      return { agent: "orchestrator", message: msg || "Pipeline error occurred", type: "alert" };
    default:
      return null;
  }
}

export default function AgentFeed({ events, isConnected }: AgentFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const feedItems = events.map(formatEvent).filter(Boolean) as { agent: string; message: string; type: string }[];

  return (
    <div className="surface-1 overflow-hidden flex flex-col" style={{ height: 340 }}>
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-zinc-800/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
          </svg>
          <span className="text-[12px] text-zinc-400 font-medium">Agent Activity</span>
        </div>
        {isConnected && (
          <span className="flex items-center gap-1.5 text-[10px] text-emerald-500">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live
          </span>
        )}
      </div>

      {/* Feed */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {feedItems.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-[11px] text-zinc-700">Waiting for agent activity...</p>
          </div>
        ) : (
          feedItems.map((item, i) => {
            const config = AGENT_CONFIG[item.agent] || AGENT_CONFIG.orchestrator;
            const name = AGENT_NAMES[item.agent] || item.agent;
            return (
              <div key={i} className="flex items-start gap-2 py-1.5 animate-slide-up" style={{ animationDelay: `${Math.min(i * 0.03, 0.3)}s` }}>
                {/* Avatar */}
                <div className={`w-6 h-6 rounded-md ${config.bg} flex items-center justify-center shrink-0 mt-0.5`}>
                  <span className={`text-[8px] font-bold ${config.color}`}>{config.initials}</span>
                </div>
                {/* Content */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-1.5">
                    <span className={`text-[11px] font-semibold ${config.color}`}>{name}</span>
                    {item.type === "working" && (
                      <span className="text-[9px] text-zinc-700 flex items-center gap-1">
                        <svg className="w-2.5 h-2.5 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        working
                      </span>
                    )}
                    {item.type === "success" && (
                      <span className="text-[9px] text-emerald-600">✓ done</span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-500 leading-relaxed mt-0.5">{item.message}</p>
                </div>
              </div>
            );
          })
        )}

        {/* Typing indicator when connected and processing */}
        {isConnected && feedItems.length > 0 && !feedItems.some(f => f.type === "alert") && (
          <div className="flex items-center gap-2 py-2 pl-8">
            <div className="flex gap-0.5">
              <span className="w-1 h-1 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0s" }} />
              <span className="w-1 h-1 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0.15s" }} />
              <span className="w-1 h-1 rounded-full bg-zinc-600 animate-bounce" style={{ animationDelay: "0.3s" }} />
            </div>
            <span className="text-[10px] text-zinc-700">agents working...</span>
          </div>
        )}
      </div>
    </div>
  );
}
