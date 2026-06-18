/**
 * VerdictFlow — Dashboard (v2)
 * Professional SaaS dashboard with table-style case list.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import UploadZone from "@/components/upload-zone";
import StatusBadge from "@/components/status-badge";
import { uploadContract, listCases, type CaseListItem } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCases = useCallback(async () => {
    try {
      const data = await listCases();
      setCases(data);
    } catch {
      // Silently fail on polling errors
    }
  }, []);

  useEffect(() => {
    fetchCases();
    const interval = setInterval(fetchCases, 5000);
    return () => clearInterval(interval);
  }, [fetchCases]);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const result = await uploadContract(file);
      router.push(`/cases/${result.case_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="header-bar sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <svg className="w-6 h-6 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
            <span className="text-[15px] font-semibold text-zinc-200 tracking-tight">VerdictFlow</span>
            <span className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded font-mono">v1.0</span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-zinc-500">
            <span className="status-dot status-dot-online" />
            All systems operational
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="mb-10 animate-slide-up">
          <h2 className="text-[28px] font-bold text-zinc-100 tracking-tight">
            Contract Review
          </h2>
          <p className="text-[14px] text-zinc-500 mt-1.5 max-w-lg">
            Upload a contract for multi-agent AI analysis — clause review, adversarial testing,
            compliance checks, and automated redlining.
          </p>
        </div>

        {/* Upload */}
        <div className="max-w-xl mb-16 animate-slide-up" style={{ animationDelay: "0.05s" }}>
          <UploadZone onUpload={handleUpload} isUploading={isUploading} />
          {error && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-red-500/8 border border-red-500/15 text-red-400 text-[12px]">
              {error}
            </div>
          )}
        </div>

        {/* Cases */}
        <div className="animate-slide-up" style={{ animationDelay: "0.1s" }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[15px] font-semibold text-zinc-300">
              Recent Cases
            </h3>
            <span className="text-[11px] text-zinc-600">
              {cases.length} {cases.length === 1 ? "case" : "cases"}
            </span>
          </div>

          {cases.length === 0 ? (
            <div className="surface-1 py-16 text-center">
              <p className="text-[13px] text-zinc-600">No cases yet</p>
              <p className="text-[11px] text-zinc-700 mt-1">Upload a contract to get started</p>
            </div>
          ) : (
            <div className="surface-1 overflow-hidden">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_100px_100px_80px_110px] gap-4 px-4 py-2.5 border-b border-zinc-800/50">
                {["Contract", "Type", "Status", "Findings", "Date"].map((h) => (
                  <span key={h} className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider">{h}</span>
                ))}
              </div>

              {/* Rows */}
              <div className="divide-y divide-zinc-800/30">
                {cases.map((c) => (
                  <button
                    key={c.case_id}
                    onClick={() => router.push(`/cases/${c.case_id}`)}
                    className="w-full grid grid-cols-[1fr_100px_100px_80px_110px] gap-4 px-4 py-3 items-center hover:bg-zinc-800/20 transition-colors text-left group"
                    id={`case-${c.case_id}`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <svg className="w-4 h-4 text-zinc-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                      <span className="text-[13px] text-zinc-300 font-medium truncate group-hover:text-zinc-100 transition-colors">
                        {c.filename}
                      </span>
                    </div>
                    <span className="text-[11px] text-zinc-500">{c.doc_type || "—"}</span>
                    <StatusBadge status={c.status} size="sm" />
                    <span className="text-[12px] text-zinc-500 font-mono">{c.total_findings}</span>
                    <span className="text-[11px] text-zinc-600">{new Date(c.created_at).toLocaleDateString()}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/30 mt-20">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between text-[11px] text-zinc-700">
          <p>VerdictFlow · Band of Agents Hackathon</p>
          <p>6 AI Agents · Tamper-Evident Audit · Human-Gated</p>
        </div>
      </footer>
    </div>
  );
}
