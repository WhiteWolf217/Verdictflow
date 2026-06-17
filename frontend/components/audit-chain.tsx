/**
 * VerdictFlow — Audit Chain Visualization
 *
 * Interactive hash-chain visualization showing tamper-evident
 * audit entries linked together.
 */

"use client";

import { useState } from "react";
import type { AuditEntry } from "@/lib/api";

interface AuditChainProps {
  entries: AuditEntry[];
  isVerified?: boolean;
  onVerify?: () => void;
}

export default function AuditChainView({
  entries,
  isVerified,
  onVerify,
}: AuditChainProps) {
  const [expandedEntry, setExpandedEntry] = useState<number | null>(null);

  return (
    <div id="audit-chain" className="space-y-4">
      {/* Verify Button */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-zinc-200 font-semibold">Hash Chain Audit Trail</h3>
          <p className="text-zinc-500 text-sm">
            {entries.length} entries, cryptographically linked
          </p>
        </div>

        <button
          onClick={onVerify}
          className={`
            px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
            ${
              isVerified === true
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : isVerified === false
                ? "bg-red-500/20 text-red-400 border border-red-500/30"
                : "bg-zinc-800 text-zinc-300 border border-zinc-700 hover:bg-zinc-700"
            }
          `}
        >
          {isVerified === true
            ? "✅ Integrity Verified"
            : isVerified === false
            ? "❌ Chain Broken"
            : "🔍 Verify Chain"}
        </button>
      </div>

      {/* Chain Entries */}
      <div className="relative">
        {/* Vertical chain line */}
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-emerald-500 via-cyan-500 to-purple-500 opacity-30" />

        {entries.map((entry, index) => (
          <div
            key={entry.step_index}
            className="relative pl-14 pb-6 group"
          >
            {/* Chain node */}
            <div className="absolute left-3 top-1 w-5 h-5 rounded-full bg-zinc-800 border-2 border-emerald-500/50 group-hover:border-emerald-400 transition-colors duration-200 z-10" />

            {/* Entry card */}
            <div
              className={`
                rounded-xl border bg-zinc-900/80 cursor-pointer
                transition-all duration-200 hover:border-zinc-600
                ${expandedEntry === index ? "border-zinc-600" : "border-zinc-800"}
              `}
              onClick={() =>
                setExpandedEntry(expandedEntry === index ? null : index)
              }
            >
              {/* Compact view */}
              <div className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-zinc-500 text-xs font-mono">
                    #{entry.step_index}
                  </span>
                  <span className="text-zinc-300 text-sm font-medium">
                    {entry.agent_name}
                  </span>
                  <span className="text-zinc-500 text-xs">
                    {entry.action}
                  </span>
                </div>
                <span className="text-zinc-600 text-xs font-mono">
                  {entry.current_hash.slice(0, 12)}...
                </span>
              </div>

              {/* Expanded view */}
              {expandedEntry === index && (
                <div className="px-4 pb-4 border-t border-zinc-800 pt-3 space-y-2">
                  {entry.data_summary && (
                    <p className="text-zinc-400 text-sm">{entry.data_summary}</p>
                  )}

                  <div className="grid grid-cols-1 gap-2 mt-2">
                    <div className="bg-zinc-950 rounded-lg p-2.5">
                      <p className="text-zinc-600 text-xs mb-1">PREVIOUS HASH</p>
                      <p className="text-zinc-400 text-xs font-mono break-all">
                        {entry.previous_hash}
                      </p>
                    </div>
                    <div className="bg-zinc-950 rounded-lg p-2.5">
                      <p className="text-zinc-600 text-xs mb-1">DATA HASH</p>
                      <p className="text-cyan-400/80 text-xs font-mono break-all">
                        {entry.data_hash}
                      </p>
                    </div>
                    <div className="bg-zinc-950 rounded-lg p-2.5">
                      <p className="text-zinc-600 text-xs mb-1">CURRENT HASH</p>
                      <p className="text-emerald-400/80 text-xs font-mono break-all">
                        {entry.current_hash}
                      </p>
                    </div>
                  </div>

                  <p className="text-zinc-600 text-xs mt-2">
                    {new Date(entry.timestamp).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
