/**
 * VerdictFlow — Case Detail Page (v2)
 * Professional tabbed interface with risk visualizations.
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
import AgentFeed from "@/components/agent-feed";
import StatusBadge from "@/components/status-badge";
import FindingCard from "@/components/finding-card";
import RedlineDiff from "@/components/redline-diff";
import AuditChainView from "@/components/audit-chain";
import RiskGauge from "@/components/risk-gauge";
import RiskRadar from "@/components/risk-radar";
import NegotiateTab from "@/components/negotiate-tab";
import BandAgents from "@/components/band-agents";
import ContractChat from "@/components/contract-chat";
import AgentBoardroom from "@/components/agent-boardroom";
import LiveBoardroom from "@/components/live-boardroom";
import AuditVerify from "@/components/audit-verify";
import MoneyHero from "@/components/money-hero";
import { downloadCounterDraft } from "@/lib/api";

type TabId = "overview" | "findings" | "redteam" | "financial" | "compliance" | "redline" | "copilot" | "boardroom" | "negotiate" | "audit";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "findings", label: "Findings" },
  { id: "redteam", label: "Red Team" },
  { id: "financial", label: "Financial" },
  { id: "compliance", label: "Compliance" },
  { id: "redline", label: "Redline" },
  { id: "copilot", label: "Copilot" },
  { id: "negotiate", label: "Negotiate" },
  { id: "audit", label: "Audit Trail" },
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

  const fetchCase = useCallback(async () => {
    if (!caseId) return;
    try {
      const data = await getCase(caseId);
      setCaseData(data);
    } catch {
      // Case might not be ready yet
    }
  }, [caseId]);

  useEffect(() => {
    fetchCase();
    const interval = setInterval(fetchCase, 3000);
    return () => clearInterval(interval);
  }, [fetchCase]);

  useEffect(() => {
    if (events.length > 0) fetchCase();
  }, [events.length, fetchCase]);

  const handleApprove = async () => {
    setIsActioning(true);
    try { await approveCase(caseId, feedback || undefined); await fetchCase(); }
    catch { alert("Approval failed"); }
    setIsActioning(false);
  };

  const handleReject = async () => {
    setIsActioning(true);
    try { await rejectCase(caseId, feedback || undefined); await fetchCase(); }
    catch { alert("Rejection failed"); }
    setIsActioning(false);
  };

  const handleVerifyAudit = async () => {
    try { const r = await verifyAuditTrail(caseId); setIsVerified(r.is_valid); }
    catch { setIsVerified(false); }
  };

  const handleFetchAudit = useCallback(async () => {
    try { const d = await getAuditTrail(caseId); setAuditEntries(d.audit_chain); }
    catch { /* not ready */ }
  }, [caseId]);

  useEffect(() => {
    if (activeTab === "audit") handleFetchAudit();
  }, [activeTab, handleFetchAudit]);

  const rs = caseData?.risk_summary;

  // Compute risk score (0-100)
  const riskScore = rs ? Math.min(100, Math.round(
    ((rs.clause_risks?.critical || 0) * 25 +
     (rs.clause_risks?.high || 0) * 15 +
     (rs.clause_risks?.medium || 0) * 8 +
     (rs.attack_severities?.critical || 0) * 20 +
     (rs.attack_severities?.high || 0) * 12 +
     (rs.compliance_status?.non_compliant || 0) * 15 +
     Math.min(rs.total_financial_exposure / 10000, 20))
  )) : 0;

  // Radar data
  const radarData = rs ? [
    { label: "Clauses", value: Math.min(1, rs.total_findings / 10) },
    { label: "Attacks", value: Math.min(1, (rs.attack_severities?.critical || 0 + rs.attack_severities?.high || 0) / 5) },
    { label: "Financial", value: Math.min(1, rs.total_financial_exposure / 100000) },
    { label: "Compliance", value: Math.min(1, (rs.compliance_status?.non_compliant || 0) / 3) },
    { label: "Edits", value: Math.min(1, rs.total_redline_edits / 8) },
    { label: "Severity", value: riskScore / 100 },
  ] : [];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="header-bar sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="text-zinc-600 hover:text-zinc-400 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="flex items-center gap-2 text-[13px]">
              <span className="text-zinc-600">Cases</span>
              <span className="text-zinc-700">/</span>
              <span className="text-zinc-300 font-medium">{caseData?.contract?.filename || "Loading..."}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isConnected && (
              <span className="flex items-center gap-1.5 text-[11px] text-emerald-500">
                <span className="status-dot status-dot-online" />
                Live
              </span>
            )}
            {caseData && <StatusBadge status={caseData.status} />}
          </div>
        </div>
      </header>

      {/* ═══ TWO-COLUMN LAYOUT: Main + Pinned Boardroom ═══ */}
      <div className="flex gap-0 relative" style={{ minHeight: "calc(100vh - 56px)" }}>

      {/* ── Left: Main Content ── */}
      <main className="flex-1 min-w-0 px-6 py-8" style={{ maxWidth: "calc(100% - 340px)" }}>
        {/* Pipeline + Live Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-6">
          <div className="lg:col-span-3 surface-1 p-5">
            <AgentProgress events={events} />
          </div>
          <div className="lg:col-span-2">
            <AgentFeed events={events} isConnected={isConnected} />
          </div>
        </div>

        {/* Human Gate */}
        {caseData?.status === "awaiting_review" && (
          <div className="surface-1 border-l-[3px] border-l-amber-500 p-5 mb-6 animate-scale-in">
            <div className="flex items-start justify-between gap-6">
              <div>
                <h3 className="text-[14px] font-semibold text-zinc-200">Human Review Required</h3>
                <p className="text-[12px] text-zinc-500 mt-1">
                  All agents have completed. Review findings and approve or reject.
                </p>
                {rs && (
                  <div className="flex gap-4 mt-2.5">
                    <span className="text-[11px] text-zinc-600">{rs.total_findings} findings</span>
                    <span className="text-[11px] text-zinc-600">{rs.total_redline_edits} edits</span>
                    {rs.total_financial_exposure > 0 && (
                      <span className="text-[11px] text-amber-500">${rs.total_financial_exposure.toLocaleString()} exposure</span>
                    )}
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-2 shrink-0">
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Optional feedback..."
                  className="w-56 h-16 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 text-[12px] p-2.5 resize-none focus:outline-none focus:border-zinc-600"
                  id="gate-feedback"
                />
                <div className="flex gap-2">
                  <button onClick={handleApprove} disabled={isActioning} className="flex-1 btn-success" id="approve-button">
                    Approve
                  </button>
                  <button onClick={handleReject} disabled={isActioning} className="flex-1 btn-danger-outline" id="reject-button">
                    Reject
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="tab-bar mb-6">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-item ${activeTab === tab.id ? "tab-item-active" : ""}`}
              id={`tab-${tab.id}`}
            >
              {tab.label}
              {tab.id === "findings" && caseData && (
                <span className="ml-1 text-[10px] opacity-50">({caseData.clause_findings.length})</span>
              )}
              {tab.id === "redteam" && caseData && (
                <span className="ml-1 text-[10px] opacity-50">({caseData.red_team_attacks.length})</span>
              )}
              {tab.id === "redline" && caseData && (
                <span className="ml-1 text-[10px] opacity-50">({caseData.redline_edits.length})</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="animate-fade-in">

          {/* ═══ OVERVIEW ═══ */}
          {activeTab === "overview" && caseData && (
            <>
              {(rs?.total_financial_exposure || 0) > 0 && (
                <MoneyHero amount={rs?.total_financial_exposure || 0} findings={rs?.total_findings || 0} />
              )}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
                {/* Risk Gauge */}
                <div className="surface-1 p-6 flex items-center justify-center">
                  <RiskGauge score={riskScore} />
                </div>

                {/* Key Metrics */}
                <div className="surface-1 p-5">
                  <p className="metric-label mb-4">Key Metrics</p>
                  <div className="space-y-4">
                    {[
                      { label: "Total Findings", value: rs?.total_findings || 0, color: "text-zinc-200" },
                      { label: "Critical Issues", value: (rs?.clause_risks?.critical || 0) + (rs?.attack_severities?.critical || 0), color: "text-red-400" },
                      { label: "High Risk", value: (rs?.clause_risks?.high || 0) + (rs?.attack_severities?.high || 0), color: "text-orange-400" },
                      { label: "Financial Exposure", value: `$${(rs?.total_financial_exposure || 0).toLocaleString()}`, color: "text-amber-400" },
                      { label: "Redline Edits", value: rs?.total_redline_edits || 0, color: "text-blue-400" },
                    ].map((m) => (
                      <div key={m.label} className="flex items-center justify-between">
                        <span className="text-[12px] text-zinc-500">{m.label}</span>
                        <span className={`text-[14px] font-semibold ${m.color}`}>{m.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Risk Radar */}
                <div className="surface-1 p-5 flex flex-col items-center justify-center">
                  <p className="metric-label mb-3">Risk Profile</p>
                  {radarData.length > 0 && <RiskRadar data={radarData} size={180} />}
                </div>
              </div>

              {/* 6 Agents on Band */}
              <BandAgents caseId={caseId} />

              {/* Contract Info + Verdict */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Contract Info */}
                <div className="surface-1 p-5">
                  <p className="metric-label mb-3">Contract Details</p>
                  <div className="space-y-2.5">
                    {[
                      { k: "Filename", v: caseData.contract?.filename },
                      { k: "Type", v: caseData.contract?.doc_type },
                      { k: "Pages", v: caseData.contract?.page_count },
                      { k: "Parties", v: caseData.contract?.parties?.join(", ") },
                      { k: "Governing Law", v: caseData.contract?.governing_law || "Not specified" },
                    ].map(({ k, v }) => (
                      <div key={k} className="flex items-baseline justify-between">
                        <span className="text-[12px] text-zinc-600">{k}</span>
                        <span className="text-[12px] text-zinc-300 font-medium text-right max-w-[60%] truncate">{v || "—"}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* AI Verdict */}
                {caseData.verdict && (
                  <div className="surface-1 p-5">
                    <div className="flex items-center justify-between mb-3">
                      <p className="metric-label">AI Verdict</p>
                      <div className="flex items-center gap-2">
                        {caseData.verdict_recommendation && (
                          <StatusBadge status={caseData.verdict_recommendation} />
                        )}
                        {caseData.confidence_score > 0 && (
                          <span className="text-[11px] text-zinc-600">
                            {(caseData.confidence_score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-[12px] text-zinc-400 leading-relaxed whitespace-pre-line">
                      {caseData.verdict}
                    </p>
                    <button
                      onClick={async () => {
                        const { downloadAudit } = await import("@/lib/api");
                        await downloadAudit(caseId);
                      }}
                      className="btn-outline mt-4 w-full text-center"
                      id="download-audit"
                    >
                      Download Audit Report
                    </button>
                  </div>
                )}
              </div>

              {/* Compliance summary */}
              {caseData.human_approval && (
                <div className="surface-1 p-5 mt-5">
                  <p className="metric-label mb-2">Human Decision</p>
                  <StatusBadge status={caseData.human_approval.approved ? "approved" : "rejected"} />
                  {caseData.human_approval.feedback && (
                    <p className="text-[12px] text-zinc-500 mt-2">{caseData.human_approval.feedback}</p>
                  )}
                </div>
              )}
            </>
          )}

          {/* ═══ FINDINGS ═══ */}
          {activeTab === "findings" && caseData && (
            <div className="space-y-2 stagger">
              {caseData.clause_findings.length === 0 ? (
                <div className="surface-1 py-16 text-center">
                  <p className="text-[13px] text-zinc-600">No findings yet — analysis in progress</p>
                </div>
              ) : (
                caseData.clause_findings.map((f) => (
                  <FindingCard
                    key={f.clause_id}
                    title={f.category.replace(/_/g, " ")}
                    category={f.category}
                    riskLevel={f.risk_level}
                    explanation={f.explanation}
                    recommendations={f.recommendations}
                    clauseText={f.clause_text}
                  />
                ))
              )}
            </div>
          )}

          {/* ═══ RED TEAM ═══ */}
          {activeTab === "redteam" && caseData && (
            <div className="space-y-2 stagger">
              {caseData.red_team_attacks.length === 0 ? (
                <div className="surface-1 py-16 text-center">
                  <p className="text-[13px] text-zinc-600">No adversarial attacks identified</p>
                </div>
              ) : (
                caseData.red_team_attacks.map((a) => (
                  <FindingCard
                    key={a.attack_id}
                    title={a.attack_vector.replace(/_/g, " ")}
                    category={a.attack_vector}
                    riskLevel={a.severity}
                    explanation={a.exploit_scenario}
                    clauseText={a.target_clause}
                  />
                ))
              )}
            </div>
          )}

          {/* ═══ FINANCIAL ═══ */}
          {activeTab === "financial" && caseData && (
            <div className="space-y-2 stagger">
              {caseData.financial_risks.length === 0 ? (
                <div className="surface-1 py-16 text-center">
                  <p className="text-[13px] text-zinc-600">No financial risks identified</p>
                </div>
              ) : (
                caseData.financial_risks.map((r) => (
                  <FindingCard
                    key={r.risk_id}
                    title={r.category.replace(/_/g, " ")}
                    category={r.category}
                    riskLevel={r.risk_score >= 0.7 ? "critical" : r.risk_score >= 0.5 ? "high" : r.risk_score >= 0.3 ? "medium" : "low"}
                    explanation={`${r.explanation}${r.exposure_amount ? ` · Exposure: $${r.exposure_amount.toLocaleString()} ${r.currency}` : ""}`}
                  />
                ))
              )}
            </div>
          )}

          {/* ═══ COMPLIANCE ═══ */}
          {activeTab === "compliance" && caseData && (
            <div className="space-y-2 stagger">
              {caseData.compliance_checks.length === 0 ? (
                <div className="surface-1 py-16 text-center">
                  <p className="text-[13px] text-zinc-600">Compliance checks pending</p>
                </div>
              ) : (
                caseData.compliance_checks.map((c) => (
                  <div key={c.check_id} className="surface-1 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[13px] text-zinc-200 font-medium">{c.regulation}</span>
                      <StatusBadge status={c.status} size="sm" />
                    </div>
                    <p className="text-[12px] text-zinc-500">{c.finding}</p>
                    {c.remediation && (
                      <div className="mt-2.5 pt-2.5 border-t border-zinc-800/30">
                        <p className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider mb-1">Remediation</p>
                        <p className="text-[12px] text-emerald-400/70">{c.remediation}</p>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* ═══ REDLINE ═══ */}
          {activeTab === "redline" && caseData && (
            <div className="space-y-3 stagger">
              {caseData.redline_edits.length > 0 && (
                <div className="surface-1 p-4 flex items-center justify-between">
                  <div>
                    <p className="text-[13px] text-zinc-200 font-medium">Negotiation counter-draft</p>
                    <p className="text-[11px] text-zinc-500">Download a redlined .docx with all {caseData.redline_edits.length} edits ready to send.</p>
                  </div>
                  <button
                    onClick={async () => { try { await downloadCounterDraft(caseId); } catch { alert("Download failed"); } }}
                    className="btn-primary whitespace-nowrap"
                    id="download-counter-draft"
                  >
                    Download .docx
                  </button>
                </div>
              )}
              {caseData.redline_edits.length === 0 ? (
                <div className="surface-1 py-16 text-center">
                  <p className="text-[13px] text-zinc-600">Redline edits pending</p>
                </div>
              ) : (
                caseData.redline_edits.map((e) => (
                  <RedlineDiff
                    key={e.edit_id}
                    originalText={e.original_text}
                    suggestedText={e.suggested_text}
                    rationale={e.rationale}
                    priority={e.priority}
                  />
                ))
              )}
            </div>
          )}

          {/* ═══ COPILOT (RAG chat) — always mounted to preserve chat history ═══ */}
          {caseData && (
            <div style={{ display: activeTab === "copilot" ? "block" : "none" }}>
              <ContractChat caseId={caseId} />
            </div>
          )}



          {/* ═══ NEGOTIATE — always mounted to preserve session & coaching ═══ */}
          {caseData && (
            <div style={{ display: activeTab === "negotiate" ? "block" : "none" }}>
              <NegotiateTab caseData={caseData} />
            </div>
          )}

          {/* ═══ AUDIT ═══ */}
          {activeTab === "audit" && (
            <div className="space-y-4">
              <AuditVerify caseId={caseId} latestHash={auditEntries.length ? auditEntries[auditEntries.length - 1].current_hash : null} />
              <AuditChainView
                entries={auditEntries}
                isVerified={isVerified}
                onVerify={handleVerifyAudit}
              />
            </div>
          )}
        </div>
      </main>

      {/* ── Right: Pinned Live Boardroom ── */}
      <aside
        className="w-[340px] shrink-0 border-l border-zinc-800/60 bg-zinc-950/80 backdrop-blur-sm sticky top-[56px] hidden lg:flex flex-col"
        style={{ height: "calc(100vh - 56px)" }}
      >
        <LiveBoardroom caseId={caseId} events={events} status={caseData?.status || "processing"} />
      </aside>

      </div>
    </div>
  );
}
