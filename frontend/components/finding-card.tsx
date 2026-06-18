/**
 * VerdictFlow — Finding Card (v2)
 * Left accent bar, expandable, professional typography.
 */

"use client";

import { useState } from "react";
import StatusBadge from "./status-badge";

interface FindingCardProps {
  title: string;
  category: string;
  riskLevel: string;
  explanation: string;
  recommendations?: string[];
  clauseText?: string;
  icon?: string;
}

const RISK_BORDER: Record<string, string> = {
  critical: "border-l-red-500",
  high: "border-l-orange-500",
  medium: "border-l-amber-500",
  low: "border-l-emerald-500",
};

export default function FindingCard({
  title,
  category,
  riskLevel,
  explanation,
  recommendations,
  clauseText,
}: FindingCardProps) {
  const [expanded, setExpanded] = useState(false);
  const borderColor = RISK_BORDER[riskLevel] || "border-l-zinc-600";

  return (
    <div
      className={`surface-1 border-l-[3px] ${borderColor} overflow-hidden cursor-pointer transition-all duration-200`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="px-4 py-3.5">
        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <h3 className="text-[13px] font-semibold text-zinc-200 capitalize truncate">
              {title}
            </h3>
            <span className="text-[10px] text-zinc-600 bg-zinc-800/80 px-1.5 py-0.5 rounded font-mono shrink-0">
              {category}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <StatusBadge status={riskLevel} size="sm" />
            <svg
              className={`w-3.5 h-3.5 text-zinc-600 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        {/* Summary - always visible */}
        <p className="text-[12px] text-zinc-500 mt-1.5 line-clamp-2 leading-relaxed">
          {explanation}
        </p>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 animate-fade-in">
          {/* Full explanation */}
          <p className="text-[13px] text-zinc-400 leading-relaxed">
            {explanation}
          </p>

          {/* Clause excerpt */}
          {clauseText && (
            <div className="mt-3 p-3 rounded-lg bg-zinc-950/80 border border-zinc-800/50">
              <p className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider mb-1.5">
                Original Clause
              </p>
              <p className="text-[12px] text-zinc-500 font-mono leading-relaxed">
                &quot;{clauseText.length > 300 ? clauseText.slice(0, 300) + "..." : clauseText}&quot;
              </p>
            </div>
          )}

          {/* Recommendations */}
          {recommendations && recommendations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-zinc-800/50">
              <p className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider mb-2">
                Recommendations
              </p>
              <ul className="space-y-1.5">
                {recommendations.map((rec, i) => (
                  <li key={i} className="text-[12px] text-zinc-400 flex items-start gap-2">
                    <span className="text-emerald-500 mt-0.5 shrink-0">→</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
