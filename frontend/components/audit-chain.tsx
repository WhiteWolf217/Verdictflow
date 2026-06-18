/**
 * VerdictFlow — Audit Chain (v2)
 * Clean timeline with hash verification.
 */

"use client";

import { useState } from "react";
import type { AuditEntry } from "@/lib/api";

interface AuditChainProps {
  entries: AuditEntry[];
  isVerified?: boolean;
  onVerify?: () => void;
}

export default function AuditChainView({ entries, isVerified, onVerify }: AuditChainProps) {
  const [expandedEntry, setExpandedEntry] = useState<number | null>(null);

  return (
    <div id="audit-chain" className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[14px] font-semibold text-zinc-200">Audit Trail</h3>
          <p className="text-[12px] text-zinc-600 mt-0.5">
            {entries.length} entries · SHA-256 hash chain
          </p>
        </div>
        <button
          onClick={onVerify}
          className={
            isVerified === true ? "btn-success" :
            isVerified === false ? "btn-danger-outline" :
            "btn-outline"
          }
        >
          {isVerified === true ? "✓ Verified" :
           isVerified === false ? "Chain Broken" :
           "Verify Integrity"}
        </button>
      </div>

      {/* Timeline */}
      <div className="relative pl-6">
        {/* Vertical line */}
        <div className="absolute left-[11px] top-2 bottom-2 w-px bg-zinc-800" />

        <div className="space-y-1">
          {entries.map((entry, index) => (
            <div key={entry.step_index} className="relative">
              {/* Dot */}
              <div className="absolute left-[-17px] top-3 w-[7px] h-[7px] rounded-full bg-zinc-600 ring-2 ring-zinc-900" />

              {/* Card */}
              <div
                className={`surface-interactive px-3.5 py-2.5 cursor-pointer ml-2 ${expandedEntry === index ? "!border-zinc-600" : ""}`}
                onClick={() => setExpandedEntry(expandedEntry === index ? null : index)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-zinc-600 font-mono">#{entry.step_index}</span>
                    <span className="text-[12px] text-zinc-300 font-medium">{entry.agent_name}</span>
                    <span className="text-[11px] text-zinc-600">{entry.action}</span>
                  </div>
                  <span className="text-[10px] text-zinc-700 font-mono">{entry.current_hash.slice(0, 10)}…</span>
                </div>

                {expandedEntry === index && (
                  <div className="mt-3 pt-3 border-t border-zinc-800/50 space-y-2 animate-fade-in">
                    {entry.data_summary && (
                      <p className="text-[12px] text-zinc-500">{entry.data_summary}</p>
                    )}
                    <div className="grid gap-1.5">
                      {[
                        { label: "Previous", value: entry.previous_hash, color: "text-zinc-500" },
                        { label: "Data", value: entry.data_hash, color: "text-sky-400/60" },
                        { label: "Current", value: entry.current_hash, color: "text-emerald-400/60" },
                      ].map(({ label, value, color }) => (
                        <div key={label} className="bg-zinc-950/80 rounded-md px-2.5 py-1.5">
                          <span className="text-[9px] text-zinc-700 font-medium uppercase tracking-wider">{label}</span>
                          <p className={`text-[10px] font-mono break-all mt-0.5 ${color}`}>{value}</p>
                        </div>
                      ))}
                    </div>
                    <p className="text-[10px] text-zinc-700">{new Date(entry.timestamp).toLocaleString()}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
