/**
 * VerdictFlow — Status Badge (v2)
 * Clean pill badges with dot indicators.
 */

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string; dot?: boolean }> = {
  // Pipeline
  uploading:       { color: "text-blue-400",    bg: "bg-blue-400/10",    label: "Uploading",       dot: true },
  intake:          { color: "text-blue-400",    bg: "bg-blue-400/10",    label: "Intake",          dot: true },
  processing:      { color: "text-blue-400",    bg: "bg-blue-400/10",    label: "Processing",      dot: true },
  analyzing:       { color: "text-amber-400",   bg: "bg-amber-400/10",   label: "Analyzing",       dot: true },
  compliance:      { color: "text-violet-400",  bg: "bg-violet-400/10",  label: "Compliance",      dot: true },
  redlining:       { color: "text-sky-400",     bg: "bg-sky-400/10",     label: "Redlining",       dot: true },
  adjudicating:    { color: "text-indigo-400",  bg: "bg-indigo-400/10",  label: "Adjudicating",    dot: true },
  awaiting_review: { color: "text-amber-400",   bg: "bg-amber-400/10",   label: "Awaiting Review", dot: true },
  approved:        { color: "text-emerald-400", bg: "bg-emerald-400/10", label: "Approved" },
  rejected:        { color: "text-red-400",     bg: "bg-red-400/10",     label: "Rejected" },
  error:           { color: "text-red-400",     bg: "bg-red-400/10",     label: "Error" },

  // Risk
  low:      { color: "text-emerald-400", bg: "bg-emerald-400/10", label: "Low" },
  medium:   { color: "text-amber-400",   bg: "bg-amber-400/10",   label: "Medium" },
  high:     { color: "text-orange-400",  bg: "bg-orange-400/10",  label: "High" },
  critical: { color: "text-red-400",     bg: "bg-red-400/10",     label: "Critical" },

  // Compliance
  compliant:     { color: "text-emerald-400", bg: "bg-emerald-400/10", label: "Compliant" },
  non_compliant: { color: "text-red-400",     bg: "bg-red-400/10",     label: "Non-Compliant" },
  needs_review:  { color: "text-amber-400",   bg: "bg-amber-400/10",   label: "Needs Review" },

  // Priority
  required:    { color: "text-red-400",    bg: "bg-red-400/10",    label: "Required" },
  recommended: { color: "text-amber-400",  bg: "bg-amber-400/10",  label: "Recommended" },
  optional:    { color: "text-blue-400",   bg: "bg-blue-400/10",   label: "Optional" },

  // Verdict
  sign:                 { color: "text-emerald-400", bg: "bg-emerald-400/10", label: "Sign" },
  sign_with_reservations: { color: "text-amber-400", bg: "bg-amber-400/10",  label: "Sign with Reservations" },
  do_not_sign:          { color: "text-red-400",     bg: "bg-red-400/10",     label: "Do Not Sign" },
};

export default function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || {
    color: "text-zinc-400", bg: "bg-zinc-400/10",
    label: status?.replace(/_/g, " ") || "Unknown",
  };

  const sizeClass = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]";

  return (
    <span className={`badge ${config.bg} ${config.color} ${sizeClass}`}>
      {config.dot && (
        <span className={`w-1.5 h-1.5 rounded-full bg-current opacity-80`} />
      )}
      {config.label}
    </span>
  );
}
