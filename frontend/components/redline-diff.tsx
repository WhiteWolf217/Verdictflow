/**
 * VerdictFlow — Redline Diff Component
 *
 * Side-by-side diff view for redline suggestions.
 */

import StatusBadge from "./status-badge";

interface RedlineDiffProps {
  originalText: string;
  suggestedText: string;
  rationale: string;
  priority: string;
}

export default function RedlineDiff({
  originalText,
  suggestedText,
  rationale,
  priority,
}: RedlineDiffProps) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/80 overflow-hidden hover:border-zinc-700 transition-colors duration-200">
      {/* Header */}
      <div className="px-5 py-3 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm">✏️</span>
          <span className="text-zinc-400 text-sm font-medium">Suggested Edit</span>
        </div>
        <StatusBadge status={priority} size="sm" />
      </div>

      {/* Diff View */}
      <div className="grid grid-cols-2 divide-x divide-zinc-800">
        {/* Original */}
        <div className="p-4">
          <p className="text-red-400/60 text-xs font-medium mb-2 uppercase tracking-wider">
            Original
          </p>
          <div className="bg-red-950/20 rounded-lg p-3 border border-red-900/30">
            <p className="text-red-300/80 text-sm font-mono leading-relaxed line-through decoration-red-500/40">
              {originalText}
            </p>
          </div>
        </div>

        {/* Suggested */}
        <div className="p-4">
          <p className="text-emerald-400/60 text-xs font-medium mb-2 uppercase tracking-wider">
            Suggested
          </p>
          <div className="bg-emerald-950/20 rounded-lg p-3 border border-emerald-900/30">
            <p className="text-emerald-300/80 text-sm font-mono leading-relaxed">
              {suggestedText}
            </p>
          </div>
        </div>
      </div>

      {/* Rationale */}
      <div className="px-5 py-3 border-t border-zinc-800 bg-zinc-950/50">
        <p className="text-zinc-500 text-xs font-medium mb-1">RATIONALE</p>
        <p className="text-zinc-400 text-sm">{rationale}</p>
      </div>
    </div>
  );
}
