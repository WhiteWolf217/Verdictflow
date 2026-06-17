/**
 * VerdictFlow — Case Detail Page
 *
 * Tabbed interface showing all agent findings, redline edits,
 * audit trail, and human gate controls.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSSE } from "@/lib/use-sse";
import {
  getCase,
  approveCase,
  rejectCase,
  getAuditTrail,
  verifyAuditTrail,
  type CaseDetail,
  type AuditEntry,
} from "@/lib/api";
import AgentProgress from "@/components/agent-progress";
import StatusBadge from "@/components/status-badge";
import FindingCard from "@/components/finding-card";
import RedlineDiff from "@/components/redline-diff";
import AuditChainView from "@/components/audit-chain";

type TabId = "overview" | "findings" | "redteam" | "financial" | "compliance" | "redline" | "audit";

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: "overview", label: "Overview", icon: "📊" },
  { id: "findings", label: "Findings", icon: "🔍" },
  { id: "redteam", label: "Red Team", icon: "🔴" },
  { id: "financial", label: "Financial", icon: "💰" },
  { id: "compliance", label: "Compliance", icon: "📋" },
  { id: "redline", label: "Redline", icon: "✏️" },
  { id: "audit", label: "Audit Trail", icon: "🔗" },
];

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params?.id as string;

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [isVerified, setIsVerified] = useState<boolean | undefined>(undefined);
  const [feedback, setFeedback] = useState("");
  const [isActioning, setIsActioning] = useState(false);

  const { events, isConnected } = useSSE(caseId);

  // Fetch case data periodically
  const fetchCase = useCallback(async () => {
    if (!caseId) return;
    try {
      const data = await getCase(caseId);
      setCaseData(data);
    } catch (e) {
      // Case might not be ready yet
    }
  }, [caseId]);

  useEffect(() => {
    fetchCase();
    const interval = setInterval(fetchCase, 3000);
    return () => clearInterval(interval);
  }, [fetchCase]);

  // Also refetch on new events
  useEffect(() => {
    if (events.length > 0) {
      fetchCase();
    }
  }, [events.length, fetchCase]);

  const handleApprove = async () => {
    setIsActioning(true);
    try {
      await approveCase(caseId, feedback || undefined);
      await fetchCase();
    } catch (e) {
      alert("Approval failed");
    }
    setIsActioning(false);
  };

  const handleReject = async () => {
    setIsActioning(true);
    try {
      await rejectCase(caseId, feedback || undefined);
      await fetchCase();
    } catch (e) {
      alert("Rejection failed");
    }
    setIsActioning(false);
  };

  const handleVerifyAudit = async () => {
    try {
      const result = await verifyAuditTrail(caseId);
      setIsVerified(result.is_valid);
    } catch (e) {
      setIsVerified(false);
    }
  };

  const handleFetchAudit = useCallback(async () => {
    try {
      const data = await getAuditTrail(caseId);
      setAuditEntries(data.audit_chain);
    } catch (e) {
      // Audit might not be ready yet
    }
  }, [caseId]);

  useEffect(() => {
    if (activeTab === "audit") {
      handleFetchAudit();
    }
  }, [activeTab, handleFetchAudit]);

  const riskSummary = caseData?.risk_summary;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-zinc-800/50 glass sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push("/")}
              className="text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center text-white font-bold text-sm">
                VF
              </div>
              <div>
                <h1 className="text-sm font-semibold text-zinc-300">
                  {caseData?.contract?.filename || "Loading..."}
                </h1>
                <p className="text-zinc-600 text-xs font-mono">
                  {caseId?.slice(0, 8)}...
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isConnected && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Live
              </span>
            )}
            {caseData && <StatusBadge status={caseData.status} />}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Agent Progress Pipeline */}
        <div className="mb-8 glass-card p-6">
          <AgentProgress events={events} />
        </div>

        {/* Human Gate (when awaiting review) */}
        {caseData?.status === "awaiting_review" && (
          <div className="mb-8 glass-card p-6 glow-emerald animate-slide-up">
            <div className="flex items-start justify-between gap-6">
              <div>
                <h3 className="text-lg font-semibold text-zinc-200 mb-1">
                  🔒 Human Review Required
                </h3>
                <p className="text-zinc-400 text-sm">
                  All agents have completed analysis. Review the findings and approve or reject this case.
                </p>
                {riskSummary && (
                  <div className="flex gap-4 mt-3">
                    <span className="text-xs text-zinc-500">
                      {riskSummary.total_findings} findings
                    </span>
                    <span className="text-xs text-zinc-500">
                      {riskSummary.total_redline_edits} edits
                    </span>
                    {riskSummary.total_financial_exposure > 0 && (
                      <span className="text-xs text-amber-400">
                        ${riskSummary.total_financial_exposure.toLocaleString()} exposure
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Optional feedback..."
                  className="w-64 h-20 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-300 text-sm p-3 resize-none focus:outline-none focus:border-emerald-500/50"
                  id="gate-feedback"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleApprove}
                    disabled={isActioning}
                    className="flex-1 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-medium transition-colors disabled:opacity-50"
                    id="approve-button"
                  >
                    ✅ Approve
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={isActioning}
                    className="flex-1 px-4 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-sm font-medium border border-red-500/30 transition-colors disabled:opacity-50"
                    id="reject-button"
                  >
                    ❌ Reject
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 overflow-x-auto pb-2">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap
                transition-all duration-200
                ${
                  activeTab === tab.id
                    ? "tab-active"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
                }
              `}
              id={`tab-${tab.id}`}
            >
              <span className="mr-1.5">{tab.icon}</span>
              {tab.label}
              {tab.id === "findings" && caseData && (
                <span className="ml-1.5 text-xs opacity-60">
                  ({caseData.clause_findings.length})
                </span>
              )}
              {tab.id === "redteam" && caseData && (
                <span className="ml-1.5 text-xs opacity-60">
                  ({caseData.red_team_attacks.length})
                </span>
              )}
              {tab.id === "redline" && caseData && (
                <span className="ml-1.5 text-xs opacity-60">
                  ({caseData.redline_edits.length})
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="animate-fade-in">
          {activeTab === "overview" && caseData && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Contract Info */}
              <div className="glass-card p-5">
                <h4 className="text-zinc-400 text-xs font-medium mb-3 uppercase tracking-wider">
                  Contract
                </h4>
                <p className="text-zinc-200 font-medium mb-2">{caseData.contract?.filename}</p>
                <div className="space-y-1.5 text-sm">
                  <p className="text-zinc-500">Type: <span className="text-zinc-300">{caseData.contract?.doc_type}</span></p>
                  <p className="text-zinc-500">Pages: <span className="text-zinc-300">{caseData.contract?.page_count}</span></p>
                  <p className="text-zinc-500">Parties: <span className="text-zinc-300">{caseData.contract?.parties?.join(", ") || "—"}</span></p>
                  <p className="text-zinc-500">Governing Law: <span className="text-zinc-300">{caseData.contract?.governing_law || "—"}</span></p>
                </div>
              </div>

              {/* Risk Summary */}
              <div className="glass-card p-5">
                <h4 className="text-zinc-400 text-xs font-medium mb-3 uppercase tracking-wider">
                  Risk Summary
                </h4>
                {riskSummary && (
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Total Findings</span>
                      <span className="text-zinc-200 font-semibold">{riskSummary.total_findings}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Critical</span>
                      <span className="text-red-400 font-semibold">{(riskSummary.clause_risks?.critical || 0) + (riskSummary.attack_severities?.critical || 0)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">High</span>
                      <span className="text-orange-400 font-semibold">{(riskSummary.clause_risks?.high || 0) + (riskSummary.attack_severities?.high || 0)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Financial Exposure</span>
                      <span className="text-amber-400 font-semibold">${riskSummary.total_financial_exposure.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Redline Edits</span>
                      <span className="text-cyan-400 font-semibold">{riskSummary.total_redline_edits}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Compliance Status */}
              <div className="glass-card p-5">
                <h4 className="text-zinc-400 text-xs font-medium mb-3 uppercase tracking-wider">
                  Compliance
                </h4>
                {riskSummary && (
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Compliant</span>
                      <span className="text-emerald-400 font-semibold">{riskSummary.compliance_status?.compliant || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Non-Compliant</span>
                      <span className="text-red-400 font-semibold">{riskSummary.compliance_status?.non_compliant || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-zinc-500">Needs Review</span>
                      <span className="text-amber-400 font-semibold">{riskSummary.compliance_status?.needs_review || 0}</span>
                    </div>
                  </div>
                )}
                {caseData.human_approval && (
                  <div className="mt-4 pt-4 border-t border-zinc-800">
                    <p className="text-zinc-500 text-xs mb-1">VERDICT</p>
                    <StatusBadge status={caseData.human_approval.approved ? "approved" : "rejected"} />
                    {caseData.human_approval.feedback && (
                      <p className="text-zinc-400 text-xs mt-2">{caseData.human_approval.feedback}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "findings" && caseData && (
            <div className="space-y-3">
              {caseData.clause_findings.length === 0 ? (
                <p className="text-zinc-500 text-center py-12">No findings yet — analysis in progress...</p>
              ) : (
                caseData.clause_findings.map((finding) => (
                  <FindingCard
                    key={finding.clause_id}
                    title={finding.category.replace(/_/g, " ")}
                    category={finding.category}
                    riskLevel={finding.risk_level}
                    explanation={finding.explanation}
                    recommendations={finding.recommendations}
                    clauseText={finding.clause_text}
                    icon="⚠️"
                  />
                ))
              )}
            </div>
          )}

          {activeTab === "redteam" && caseData && (
            <div className="space-y-3">
              {caseData.red_team_attacks.length === 0 ? (
                <p className="text-zinc-500 text-center py-12">No attacks found yet...</p>
              ) : (
                caseData.red_team_attacks.map((attack) => (
                  <FindingCard
                    key={attack.attack_id}
                    title={attack.attack_vector.replace(/_/g, " ")}
                    category={attack.attack_vector}
                    riskLevel={attack.severity}
                    explanation={attack.exploit_scenario}
                    clauseText={attack.target_clause}
                    icon="🔴"
                  />
                ))
              )}
            </div>
          )}

          {activeTab === "financial" && caseData && (
            <div className="space-y-3">
              {caseData.financial_risks.length === 0 ? (
                <p className="text-zinc-500 text-center py-12">No financial risks identified yet...</p>
              ) : (
                caseData.financial_risks.map((risk) => (
                  <FindingCard
                    key={risk.risk_id}
                    title={risk.category.replace(/_/g, " ")}
                    category={risk.category}
                    riskLevel={risk.risk_score >= 0.7 ? "critical" : risk.risk_score >= 0.5 ? "high" : risk.risk_score >= 0.3 ? "medium" : "low"}
                    explanation={`${risk.explanation}${risk.exposure_amount ? ` (Exposure: $${risk.exposure_amount.toLocaleString()} ${risk.currency})` : ""}`}
                    icon="💰"
                  />
                ))
              )}
            </div>
          )}

          {activeTab === "compliance" && caseData && (
            <div className="space-y-3">
              {caseData.compliance_checks.length === 0 ? (
                <p className="text-zinc-500 text-center py-12">Compliance checks pending...</p>
              ) : (
                caseData.compliance_checks.map((check) => (
                  <div key={check.check_id} className="glass-card p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">📋</span>
                        <span className="text-zinc-200 font-semibold text-sm">{check.regulation}</span>
                      </div>
                      <StatusBadge status={check.status} size="sm" />
                    </div>
                    <p className="text-zinc-400 text-sm mb-2">{check.finding}</p>
                    {check.remediation && (
                      <div className="mt-2 pt-2 border-t border-zinc-800">
                        <p className="text-zinc-500 text-xs mb-1">REMEDIATION</p>
                        <p className="text-emerald-400/80 text-sm">{check.remediation}</p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "redline" && caseData && (
            <div className="space-y-4">
              {caseData.redline_edits.length === 0 ? (
                <p className="text-zinc-500 text-center py-12">Redline edits pending...</p>
              ) : (
                caseData.redline_edits.map((edit) => (
                  <RedlineDiff
                    key={edit.edit_id}
                    originalText={edit.original_text}
                    suggestedText={edit.suggested_text}
                    rationale={edit.rationale}
                    priority={edit.priority}
                  />
                ))
              )}
            </div>
          )}

          {activeTab === "audit" && (
            <AuditChainView
              entries={auditEntries}
              isVerified={isVerified}
              onVerify={handleVerifyAudit}
            />
          )}
        </div>
      </main>
    </div>
  );
}
