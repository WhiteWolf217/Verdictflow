/**
 * VerdictFlow — Agent Progress Component
 *
 * Animated pipeline visualization showing agent status.
 */

"use client";

import { SSEEvent } from "@/lib/use-sse";

interface AgentProgressProps {
  events: SSEEvent[];
}

const PIPELINE_STAGES = [
  { id: "intake", label: "Intake", icon: "📄" },
  { id: "clause_analyst", label: "Clause Analysis", icon: "🔍" },
  { id: "red_team", label: "Red Team", icon: "🔴" },
  { id: "financial_risk", label: "Financial Risk", icon: "💰" },
  { id: "compliance", label: "Compliance", icon: "📋" },
  { id: "redline", label: "Redline", icon: "✏️" },
  { id: "human_gate", label: "Human Gate", icon: "🔒" },
];

type StageStatus = "pending" | "running" | "complete" | "error";

export default function AgentProgress({ events }: AgentProgressProps) {
  // Derive stage statuses from events
  const getStageStatus = (stageId: string): StageStatus => {
    const stageEvents = events.filter(
      (e) => e.data?.agent === stageId || e.data?.stage === stageId
    );

    if (stageEvents.some((e) => e.event_type === "agent_completed")) return "complete";
    if (stageEvents.some((e) => e.event_type === "agent_started" || e.event_type === "stage_started"))
      return "running";
    if (stageEvents.some((e) => e.event_type === "case_error")) return "error";

    // Check for gate
    if (stageId === "human_gate") {
      if (events.some((e) => e.event_type === "case_finalized")) return "complete";
      if (events.some((e) => e.event_type === "gate_requested")) return "running";
    }

    return "pending";
  };

  const getStatusColor = (status: StageStatus): string => {
    switch (status) {
      case "complete":
        return "bg-emerald-500 shadow-emerald-500/50";
      case "running":
        return "bg-amber-500 shadow-amber-500/50 animate-pulse";
      case "error":
        return "bg-red-500 shadow-red-500/50";
      default:
        return "bg-zinc-700";
    }
  };

  const getTextColor = (status: StageStatus): string => {
    switch (status) {
      case "complete":
        return "text-emerald-400";
      case "running":
        return "text-amber-400";
      case "error":
        return "text-red-400";
      default:
        return "text-zinc-500";
    }
  };

  const getLineColor = (status: StageStatus): string => {
    switch (status) {
      case "complete":
        return "bg-emerald-500";
      default:
        return "bg-zinc-700";
    }
  };

  // Get the message for a stage
  const getStageMessage = (stageId: string): string => {
    const stageEvents = events.filter(
      (e) => e.data?.agent === stageId || e.data?.stage === stageId
    );

    const latestEvent = stageEvents[stageEvents.length - 1];
    return (latestEvent?.data?.message as string) || "";
  };

  return (
    <div id="agent-progress" className="w-full">
      <div className="flex items-center justify-between relative">
        {PIPELINE_STAGES.map((stage, index) => {
          const status = getStageStatus(stage.id);
          const message = getStageMessage(stage.id);

          return (
            <div key={stage.id} className="flex items-center flex-1">
              {/* Node */}
              <div className="flex flex-col items-center relative group">
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center
                    text-lg transition-all duration-500 shadow-lg
                    ${getStatusColor(status)}
                  `}
                >
                  {status === "complete" ? (
                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : status === "running" ? (
                    <span className="text-sm">{stage.icon}</span>
                  ) : (
                    <span className="text-sm opacity-50">{stage.icon}</span>
                  )}
                </div>

                <span className={`mt-2 text-xs font-medium whitespace-nowrap ${getTextColor(status)}`}>
                  {stage.label}
                </span>

                {/* Tooltip with message */}
                {message && (
                  <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
                    <div className="bg-zinc-800 text-zinc-300 text-xs px-3 py-1.5 rounded-lg shadow-xl whitespace-nowrap border border-zinc-700">
                      {message}
                    </div>
                  </div>
                )}
              </div>

              {/* Connecting line */}
              {index < PIPELINE_STAGES.length - 1 && (
                <div className={`flex-1 h-0.5 mx-1 transition-all duration-500 ${getLineColor(status)}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
