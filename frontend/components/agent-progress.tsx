/**
 * VerdictFlow — Agent Progress Stepper (v3)
 * Animated pipeline with document flowing between stages.
 */

"use client";

import { useEffect, useState } from "react";
import { SSEEvent } from "@/lib/use-sse";

interface AgentProgressProps {
  events: SSEEvent[];
}

const STAGES = [
  { id: "intake", label: "Intake", desc: "Parse & classify" },
  { id: "clause_analyst", label: "Clauses", desc: "Analyze terms" },
  { id: "red_team", label: "Red Team", desc: "Find exploits" },
  { id: "financial_risk", label: "Financial", desc: "Assess exposure" },
  { id: "compliance", label: "Compliance", desc: "Check regulations" },
  { id: "redline", label: "Redline", desc: "Suggest edits" },
  { id: "human_gate", label: "Review", desc: "Human decision" },
];

type Status = "pending" | "running" | "complete" | "error";

export default function AgentProgress({ events }: AgentProgressProps) {
  const [elapsed, setElapsed] = useState(0);

  // Timer for elapsed time
  useEffect(() => {
    if (events.length === 0) return;
    const start = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [events.length > 0]);

  const getStatus = (stageId: string): Status => {
    const stageEvents = events.filter(
      (e) => e.data?.agent === stageId || e.data?.stage === stageId
    );
    if (stageEvents.some((e) => e.event_type === "agent_completed")) return "complete";
    if (stageEvents.some((e) => e.event_type === "agent_started" || e.event_type === "stage_started")) return "running";
    if (stageEvents.some((e) => e.event_type === "case_error")) return "error";
    if (stageId === "human_gate") {
      if (events.some((e) => e.event_type === "case_finalized")) return "complete";
      if (events.some((e) => e.event_type === "gate_requested")) return "running";
    }
    return "pending";
  };

  const getMessage = (stageId: string): string => {
    const stageEvents = events.filter(
      (e) => e.data?.agent === stageId || e.data?.stage === stageId
    );
    const latest = stageEvents[stageEvents.length - 1];
    return (latest?.data?.message as string) || "";
  };

  const completedCount = STAGES.filter((s) => getStatus(s.id) === "complete").length;
  const activeIndex = STAGES.findIndex((s) => getStatus(s.id) === "running");
  const progress = ((completedCount + (activeIndex >= 0 ? 0.5 : 0)) / STAGES.length) * 100;

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <div id="agent-progress">
      {/* Top bar: progress + timer */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <p className="text-[12px] text-zinc-500 font-medium">Pipeline</p>
          <div className="flex items-center gap-1.5">
            <div className="w-32 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-blue-500 transition-all duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-[10px] text-zinc-600">{completedCount}/{STAGES.length}</span>
          </div>
        </div>
        {events.length > 0 && (
          <span className="text-[11px] text-zinc-600 font-mono">{formatTime(elapsed)}</span>
        )}
      </div>

      {/* Stepper */}
      <div className="flex items-start">
        {STAGES.map((stage, i) => {
          const status = getStatus(stage.id);
          const message = getMessage(stage.id);
          const isActive = status === "running";

          return (
            <div key={stage.id} className="flex items-start flex-1 group">
              <div className="flex flex-col items-center min-w-0">
                {/* Node */}
                <div className="relative">
                  <div className={`stepper-node ${
                    status === "complete" ? "stepper-node-complete" :
                    status === "running" ? "stepper-node-active" :
                    status === "error" ? "stepper-node-error" : ""
                  }`}>
                    {status === "complete" ? (
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <span>{i + 1}</span>
                    )}
                  </div>

                  {/* Document icon flying to next stage */}
                  {isActive && i < STAGES.length - 1 && (
                    <div className="absolute left-8 top-1/2 -translate-y-1/2"
                      style={{
                        animation: "flyDoc 1.5s ease-in-out infinite",
                      }}
                    >
                      <svg className="w-3 h-3 text-blue-400/60" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 2l5 5h-5V4zm-3 9h4v2h-4v-2zm0 4h4v2h-4v-2zm-2-4h1v2H8v-2zm0 4h1v2H8v-2z"/>
                      </svg>
                    </div>
                  )}
                </div>

                {/* Label */}
                <span className={`mt-2 text-[10px] font-semibold whitespace-nowrap ${
                  status === "complete" ? "text-emerald-400" :
                  status === "running" ? "text-blue-400" :
                  status === "error" ? "text-red-400" :
                  "text-zinc-600"
                }`}>
                  {stage.label}
                </span>

                {/* Description / message */}
                <span className={`text-[9px] mt-0.5 whitespace-nowrap ${
                  isActive ? "text-blue-400/60" : "text-zinc-700"
                }`}>
                  {isActive && message ? message.slice(0, 25) : stage.desc}
                </span>
              </div>

              {/* Line */}
              {i < STAGES.length - 1 && (
                <div className="flex-1 mt-4 mx-1 relative">
                  <div className="stepper-line" />
                  {status === "complete" && (
                    <div className="absolute inset-0 stepper-line stepper-line-complete" style={{
                      animation: "draw-line 0.5s ease forwards",
                    }} />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
