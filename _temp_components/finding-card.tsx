/**
 * VerdictFlow — Finding Card Component
 *
 * Reusable card for displaying findings with risk-level badges.
 */

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

export default function FindingCard({
  title,
  category,
  riskLevel,
  explanation,
  recommendations,
  clauseText,
  icon = "⚠️",
}: FindingCardProps) {
  return (
    <div
      className={`
        rounded-xl border border-zinc-800 bg-zinc-900/80 p-5
        hover:border-zinc-700 transition-all duration-200
        hover:shadow-lg hover:shadow-zinc-900/50
      `}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <h3 className="text-zinc-200 font-semibold text-sm">{title}</h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
            {category}
          </span>
          <StatusBadge status={riskLevel} size="sm" />
        </div>
      </div>

      <p className="text-zinc-400 text-sm leading-relaxed mb-3">
        {explanation}
      </p>

      {clauseText && (
        <div className="bg-zinc-950 rounded-lg p-3 mb-3 border border-zinc-800">
          <p className="text-zinc-500 text-xs font-mono leading-relaxed">
            &quot;{clauseText.length > 200 ? clauseText.slice(0, 200) + "..." : clauseText}&quot;
          </p>
        </div>
      )}

      {recommendations && recommendations.length > 0 && (
        <div className="mt-3 pt-3 border-t border-zinc-800">
          <p className="text-zinc-500 text-xs font-medium mb-1.5">
            RECOMMENDATIONS
          </p>
          <ul className="space-y-1">
            {recommendations.map((rec, i) => (
              <li key={i} className="text-emerald-400/80 text-xs flex items-start gap-1.5">
                <span className="text-emerald-500 mt-0.5">→</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
