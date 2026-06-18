/**
 * VerdictFlow — Contract Version Compare
 * 
 * Upload v1 and v2 of a contract side-by-side. Agents analyze both
 * and report risk deltas — what changed, new risks, mitigated risks.
 */

"use client";

import { useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Types ──────────────────────────────────────────────────── */

interface ChangeItem {
  clause_area: string;
  change_type: "added" | "removed" | "modified";
  v1_text: string | null;
  v2_text: string | null;
  risk_impact: "increased" | "decreased" | "neutral";
  severity: "low" | "medium" | "high" | "critical";
  explanation: string;
}

interface CompareResult {
  overall_risk_delta: "increased" | "decreased" | "unchanged";
  overall_summary: string;
  risk_score_v1: number;
  risk_score_v2: number;
  changes: ChangeItem[];
  new_risks: string[];
  mitigated_risks: string[];
  recommendation: string;
  v1_filename: string;
  v2_filename: string;
}

/* ── Styles ──────────────────────────────────────────────────── */

const SEVERITY_COLOR: Record<string, string> = {
  low: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  medium: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  high: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  critical: "text-red-400 bg-red-400/10 border-red-400/20",
};

const CHANGE_ICON: Record<string, { icon: string; color: string; bg: string }> = {
  added:    { icon: "+", color: "text-emerald-400", bg: "bg-emerald-400/15" },
  removed:  { icon: "−", color: "text-red-400",     bg: "bg-red-400/15" },
  modified: { icon: "~", color: "text-amber-400",   bg: "bg-amber-400/15" },
};

const RISK_ARROW: Record<string, { arrow: string; color: string }> = {
  increased:  { arrow: "↑", color: "text-red-400" },
  decreased:  { arrow: "↓", color: "text-emerald-400" },
  neutral:    { arrow: "→", color: "text-zinc-500" },
  unchanged:  { arrow: "→", color: "text-zinc-500" },
};

/* ── Component ──────────────────────────────────────────────── */

export default function VersionCompare() {
  const [v1File, setV1File] = useState<File | null>(null);
  const [v2File, setV2File] = useState<File | null>(null);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const v1Ref = useRef<HTMLInputElement>(null);
  const v2Ref = useRef<HTMLInputElement>(null);

  const runCompare = async () => {
    if (!v1File || !v2File) return;
    setIsLoading(true);
    setError("");
    setResult(null);

    const form = new FormData();
    form.append("v1", v1File);
    form.append("v2", v2File);

    try {
      const res = await fetch(`${API}/api/contracts/compare`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed");
    }
    setIsLoading(false);
  };

  const delta = result ? RISK_ARROW[result.overall_risk_delta] || RISK_ARROW.unchanged : null;

  return (
    <div className="space-y-6">
      {/* Upload Zone */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* V1 */}
        <DropZone
          label="Version 1 (Original)"
          sublabel="The earlier / current version"
          file={v1File}
          onFile={setV1File}
          inputRef={v1Ref}
          accent="border-blue-500/30"
          accentBg="bg-blue-500/5"
        />
        {/* V2 */}
        <DropZone
          label="Version 2 (Revised)"
          sublabel="The updated / proposed version"
          file={v2File}
          onFile={setV2File}
          inputRef={v2Ref}
          accent="border-emerald-500/30"
          accentBg="bg-emerald-500/5"
        />
      </div>

      {/* Compare Button */}
      <div className="flex justify-center">
        <button
          onClick={runCompare}
          disabled={!v1File || !v2File || isLoading}
          className="btn-primary px-8 py-2.5 text-[13px] flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Analyzing changes...
            </>
          ) : (
            <>
              <span>⚖️</span>
              Compare & Analyse Risk Delta
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="surface-1 p-4 border-l-[3px] border-l-red-500">
          <p className="text-[12px] text-red-400">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-5 animate-fade-in">
          {/* Delta Hero */}
          <div className="surface-1 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-[11px] text-zinc-600 uppercase tracking-wider font-semibold mb-1">Overall Risk Delta</p>
                <div className="flex items-center gap-3">
                  <span className={`text-4xl font-bold ${delta?.color}`}>{delta?.arrow}</span>
                  <span className={`text-[18px] font-semibold ${delta?.color}`}>
                    Risk {result.overall_risk_delta === "unchanged" ? "Unchanged" : result.overall_risk_delta === "increased" ? "Increased" : "Decreased"}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="text-center">
                  <p className="text-[10px] text-zinc-600 uppercase mb-1">V1 Risk</p>
                  <p className="text-[24px] font-bold text-zinc-300">{result.risk_score_v1}</p>
                </div>
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </div>
                <div className="text-center">
                  <p className="text-[10px] text-zinc-600 uppercase mb-1">V2 Risk</p>
                  <p className={`text-[24px] font-bold ${
                    result.risk_score_v2 > result.risk_score_v1 ? "text-red-400" :
                    result.risk_score_v2 < result.risk_score_v1 ? "text-emerald-400" : "text-zinc-300"
                  }`}>{result.risk_score_v2}</p>
                </div>
              </div>
            </div>
            <p className="text-[13px] text-zinc-400 leading-relaxed">{result.overall_summary}</p>
          </div>

          {/* New Risks + Mitigated */}
          {(result.new_risks.length > 0 || result.mitigated_risks.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {result.new_risks.length > 0 && (
                <div className="surface-1 p-4 border-l-[3px] border-l-red-500">
                  <p className="text-[11px] font-semibold text-red-400 uppercase tracking-wider mb-2">⚠️ New Risks in V2</p>
                  <ul className="space-y-1.5">
                    {result.new_risks.map((r, i) => (
                      <li key={i} className="text-[12px] text-zinc-400 flex items-start gap-2">
                        <span className="text-red-400 mt-0.5 shrink-0">•</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {result.mitigated_risks.length > 0 && (
                <div className="surface-1 p-4 border-l-[3px] border-l-emerald-500">
                  <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider mb-2">✅ Mitigated in V2</p>
                  <ul className="space-y-1.5">
                    {result.mitigated_risks.map((r, i) => (
                      <li key={i} className="text-[12px] text-zinc-400 flex items-start gap-2">
                        <span className="text-emerald-400 mt-0.5 shrink-0">•</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Changes Table */}
          <div className="surface-1 overflow-hidden">
            <div className="px-5 py-3 border-b border-zinc-800/60">
              <p className="text-[13px] font-semibold text-zinc-200">
                Clause-by-Clause Changes
                <span className="ml-2 text-[11px] text-zinc-600 font-normal">({result.changes.length} changes detected)</span>
              </p>
            </div>
            <div className="divide-y divide-zinc-800/40">
              {result.changes.map((c, i) => {
                const ct = CHANGE_ICON[c.change_type] || CHANGE_ICON.modified;
                const ri = RISK_ARROW[c.risk_impact] || RISK_ARROW.neutral;
                const sev = SEVERITY_COLOR[c.severity] || SEVERITY_COLOR.medium;

                return (
                  <div key={i} className="px-5 py-4 animate-slide-up" style={{ animationDelay: `${i * 0.05}s` }}>
                    <div className="flex items-center gap-2 mb-2">
                      {/* Change type badge */}
                      <span className={`w-5 h-5 rounded flex items-center justify-center text-[11px] font-bold ${ct.bg} ${ct.color}`}>
                        {ct.icon}
                      </span>
                      <span className="text-[13px] font-semibold text-zinc-200">{c.clause_area}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${sev}`}>
                        {c.severity}
                      </span>
                      <span className={`text-[13px] font-bold ${ri.color} ml-auto`}>
                        Risk {ri.arrow}
                      </span>
                    </div>

                    {/* V1 → V2 text diff */}
                    {c.change_type === "modified" && (
                      <div className="grid grid-cols-2 gap-3 mb-2">
                        {c.v1_text && (
                          <div className="p-2.5 rounded-lg bg-red-500/5 border border-red-500/10">
                            <p className="text-[9px] text-red-400/60 uppercase font-semibold mb-1">V1 (Original)</p>
                            <p className="text-[11px] text-zinc-500 leading-relaxed">{c.v1_text}</p>
                          </div>
                        )}
                        {c.v2_text && (
                          <div className="p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                            <p className="text-[9px] text-emerald-400/60 uppercase font-semibold mb-1">V2 (Revised)</p>
                            <p className="text-[11px] text-zinc-400 leading-relaxed">{c.v2_text}</p>
                          </div>
                        )}
                      </div>
                    )}
                    {c.change_type === "added" && c.v2_text && (
                      <div className="p-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/10 mb-2">
                        <p className="text-[9px] text-emerald-400/60 uppercase font-semibold mb-1">Added in V2</p>
                        <p className="text-[11px] text-zinc-400 leading-relaxed">{c.v2_text}</p>
                      </div>
                    )}
                    {c.change_type === "removed" && c.v1_text && (
                      <div className="p-2.5 rounded-lg bg-red-500/5 border border-red-500/10 mb-2">
                        <p className="text-[9px] text-red-400/60 uppercase font-semibold mb-1">Removed from V1</p>
                        <p className="text-[11px] text-zinc-500 leading-relaxed line-through">{c.v1_text}</p>
                      </div>
                    )}

                    <p className="text-[11px] text-zinc-500 leading-relaxed">{c.explanation}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recommendation */}
          {result.recommendation && (
            <div className="surface-1 p-4 border-l-[3px] border-l-blue-500">
              <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-1">💡 Recommendation</p>
              <p className="text-[12px] text-zinc-400 leading-relaxed">{result.recommendation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Drop Zone Sub-component ─────────────────────────────────── */

function DropZone({
  label, sublabel, file, onFile, inputRef, accent, accentBg,
}: {
  label: string;
  sublabel: string;
  file: File | null;
  onFile: (f: File) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  accent: string;
  accentBg: string;
}) {
  const [isDrag, setIsDrag] = useState(false);

  return (
    <div
      className={`surface-1 p-5 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
        isDrag ? `${accent} ${accentBg}` : file ? `${accent} border-opacity-50` : "border-zinc-800 hover:border-zinc-700"
      }`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setIsDrag(true); }}
      onDragLeave={() => setIsDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDrag(false);
        const f = e.dataTransfer.files[0];
        if (f) onFile(f);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.docx,.txt,.doc"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
      />
      <div className="text-center">
        <p className="text-[13px] font-semibold text-zinc-300 mb-0.5">{label}</p>
        <p className="text-[11px] text-zinc-600 mb-3">{sublabel}</p>
        {file ? (
          <div className="flex items-center justify-center gap-2">
            <span className="text-[16px]">📄</span>
            <span className="text-[12px] text-zinc-400 font-medium">{file.name}</span>
            <span className="text-[10px] text-zinc-600">({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
        ) : (
          <p className="text-[11px] text-zinc-600">Drop file or click to browse</p>
        )}
      </div>
    </div>
  );
}
