/**
 * VerdictFlow — Dashboard Page
 *
 * Landing page with case list and contract upload.
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

  // Fetch cases on mount and every 5 seconds
  const fetchCases = useCallback(async () => {
    try {
      const data = await listCases();
      setCases(data);
    } catch (e) {
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
      <header className="border-b border-zinc-800/50 glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center text-white font-bold text-sm">
              VF
            </div>
            <div>
              <h1 className="text-lg font-bold gradient-text">VerdictFlow</h1>
              <p className="text-zinc-500 text-xs">Contract Intelligence</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              System Online
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Hero Section */}
        <div className="text-center mb-12 animate-slide-up">
          <h2 className="text-4xl font-bold mb-3">
            <span className="gradient-text">Intelligent Contract Review</span>
          </h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Upload a contract and let 6 specialized AI agents analyze, red-team,
            and redline it — producing a tamper-evident audit packet.
          </p>
        </div>

        {/* Upload Zone */}
        <div className="max-w-2xl mx-auto mb-16 animate-slide-up" style={{ animationDelay: "0.1s" }}>
          <UploadZone onUpload={handleUpload} isUploading={isUploading} />

          {error && (
            <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Cases List */}
        <div className="animate-slide-up" style={{ animationDelay: "0.2s" }}>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-zinc-200">
              Recent Cases
            </h3>
            <span className="text-zinc-500 text-sm">
              {cases.length} {cases.length === 1 ? "case" : "cases"}
            </span>
          </div>

          {cases.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <p className="text-zinc-500 text-lg">No cases yet</p>
              <p className="text-zinc-600 text-sm mt-1">
                Upload a contract to get started
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {cases.map((caseItem) => (
                <button
                  key={caseItem.case_id}
                  onClick={() => router.push(`/cases/${caseItem.case_id}`)}
                  className="w-full glass-card p-5 flex items-center justify-between hover:border-zinc-600 transition-all duration-200 text-left group"
                  id={`case-${caseItem.case_id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center text-lg group-hover:bg-zinc-700 transition-colors">
                      📄
                    </div>
                    <div>
                      <p className="text-zinc-200 font-medium group-hover:text-white transition-colors">
                        {caseItem.filename}
                      </p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-zinc-500 text-xs">
                          {caseItem.doc_type}
                        </span>
                        <span className="text-zinc-700">•</span>
                        <span className="text-zinc-500 text-xs">
                          {new Date(caseItem.created_at).toLocaleDateString()}
                        </span>
                        {caseItem.total_findings > 0 && (
                          <>
                            <span className="text-zinc-700">•</span>
                            <span className="text-zinc-500 text-xs">
                              {caseItem.total_findings} findings
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusBadge status={caseItem.status} />
                    <svg
                      className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 mt-20">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-zinc-600 text-xs">
          <p>VerdictFlow — Band of Agents Hackathon</p>
          <p>6 AI Agents • Tamper-Evident Audit • Human-Gated</p>
        </div>
      </footer>
    </div>
  );
}
