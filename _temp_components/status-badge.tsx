/**
 * VerdictFlow — Status Badge Component
 *
 * Animated status badges with risk-level color coding.
 */

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md" | "lg";
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  // Case statuses
  uploading: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Uploading" },
  intake: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Intake" },
  analyzing: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Analyzing" },
  compliance: { bg: "bg-purple-500/20", text: "text-purple-400", label: "Compliance" },
  redlining: { bg: "bg-cyan-500/20", text: "text-cyan-400", label: "Redlining" },
  awaiting_review: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Awaiting Review" },
  approved: { bg: "bg-emerald-500/20", text: "text-emerald-400", label: "Approved" },
  rejected: { bg: "bg-red-500/20", text: "text-red-400", label: "Rejected" },
  error: { bg: "bg-red-500/20", text: "text-red-400", label: "Error" },

  // Risk levels
  low: { bg: "bg-emerald-500/20", text: "text-emerald-400", label: "Low" },
  medium: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Medium" },
  high: { bg: "bg-orange-500/20", text: "text-orange-400", label: "High" },
  critical: { bg: "bg-red-500/20", text: "text-red-400", label: "Critical" },

  // Compliance
  compliant: { bg: "bg-emerald-500/20", text: "text-emerald-400", label: "Compliant" },
  non_compliant: { bg: "bg-red-500/20", text: "text-red-400", label: "Non-Compliant" },
  needs_review: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Needs Review" },

  // Edit priorities
  required: { bg: "bg-red-500/20", text: "text-red-400", label: "Required" },
  recommended: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Recommended" },
  optional: { bg: "bg-blue-500/20", text: "text-blue-400", label: "Optional" },
};

const SIZE_STYLES = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-3 py-1 text-sm",
  lg: "px-4 py-1.5 text-base",
};

export default function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] || {
    bg: "bg-zinc-500/20",
    text: "text-zinc-400",
    label: status,
  };

  const isAnimated = ["analyzing", "uploading", "intake", "compliance", "redlining", "awaiting_review"].includes(status);

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full font-medium
        ${style.bg} ${style.text} ${SIZE_STYLES[size]}
        ${isAnimated ? "animate-pulse" : ""}
      `}
    >
      {isAnimated && (
        <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />
      )}
      {style.label}
    </span>
  );
}
