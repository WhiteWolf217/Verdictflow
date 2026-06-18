/**
 * VerdictFlow — Redline Diff (v2)
 * Unified diff view with line markers, like GitHub.
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
    <div className="surface-1 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-2.5 flex items-center justify-between border-b border-zinc-800/50">
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
          </svg>
          <span className="text-[12px] text-zinc-400 font-medium">Suggested Edit</span>
        </div>
        <StatusBadge status={priority} size="sm" />
      </div>

      {/* Diff */}
      <div className="font-mono text-[12px] leading-relaxed">
        <div className="diff-remove px-4 py-2.5">
          <span className="text-red-500/60 mr-2 select-none">−</span>
          <span className="text-red-300/70">{originalText}</span>
        </div>
        <div className="diff-add px-4 py-2.5">
          <span className="text-emerald-500/60 mr-2 select-none">+</span>
          <span className="text-emerald-300/70">{suggestedText}</span>
        </div>
      </div>

      {/* Rationale */}
      <div className="px-4 py-2.5 border-t border-zinc-800/50">
        <p className="text-[11px] text-zinc-400 leading-relaxed">
          <span className="text-zinc-600 font-medium">Rationale: </span>
          {rationale}
        </p>
      </div>
    </div>
  );
}
