/**
 * VerdictFlow — API Client
 *
 * Typed methods for all backend endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface ContractMetadata {
  doc_id: string;
  filename: string;
  upload_timestamp: string;
  page_count: number;
  total_chars: number;
  doc_type: string;
  parties: string[];
  effective_date: string | null;
  governing_law: string | null;
  key_terms_summary: string | null;
}

export interface ClauseFinding {
  clause_id: string;
  clause_text: string;
  category: string;
  risk_level: "low" | "medium" | "high" | "critical";
  explanation: string;
  agent_source: string;
  recommendations: string[];
  page_number: number | null;
}

export interface RedTeamAttack {
  attack_id: string;
  attack_vector: string;
  target_clause: string;
  exploit_scenario: string;
  severity: "low" | "medium" | "high" | "critical";
  agent_source: string;
  defender_assessment: string | null;
}

export interface FinancialRisk {
  risk_id: string;
  category: string;
  exposure_amount: number | null;
  currency: string;
  explanation: string;
  risk_score: number;
  agent_source: string;
  page_number: number | null;
}

export interface ComplianceCheck {
  check_id: string;
  regulation: string;
  status: "compliant" | "non_compliant" | "needs_review";
  finding: string;
  remediation: string;
  agent_source: string;
  relevant_clause: string | null;
}

export interface RedlineEdit {
  edit_id: string;
  original_text: string;
  suggested_text: string;
  rationale: string;
  priority: "required" | "recommended" | "optional";
  agent_source: string;
  related_finding_ids: string[];
}

export interface HumanApproval {
  approved: boolean;
  reviewer_name: string | null;
  feedback: string | null;
  timestamp: string;
}

export interface RiskSummary {
  clause_risks: Record<string, number>;
  attack_severities: Record<string, number>;
  compliance_status: Record<string, number>;
  total_financial_exposure: number;
  total_findings: number;
  total_redline_edits: number;
}

export interface CaseDetail {
  case_id: string;
  status: string;
  contract: ContractMetadata | null;
  clause_findings: ClauseFinding[];
  red_team_attacks: RedTeamAttack[];
  financial_risks: FinancialRisk[];
  compliance_checks: ComplianceCheck[];
  redline_edits: RedlineEdit[];
  human_approval: HumanApproval | null;
  risk_summary: RiskSummary;
  created_at: string;
  finalized_at: string | null;
}

export interface CaseListItem {
  case_id: string;
  filename: string;
  status: string;
  doc_type: string;
  created_at: string;
  total_findings: number;
}

export interface AuditEntry {
  step_index: number;
  agent_name: string;
  action: string;
  data_hash: string;
  previous_hash: string;
  current_hash: string;
  timestamp: string;
  data_summary: string | null;
}

export interface AuditTrail {
  case_id: string;
  status: string;
  audit_chain: AuditEntry[];
  chain_length: number;
  latest_hash: string | null;
}

export interface AuditVerification {
  case_id: string;
  is_valid: boolean;
  chain_length: number;
  latest_hash: string;
  error: string | null;
}

// ── API Methods ─────────────────────────────────────────────────────────────

export async function uploadContract(file: File): Promise<{
  case_id: string;
  filename: string;
  status: string;
  stream_url: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/contracts/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function listCases(): Promise<CaseListItem[]> {
  const res = await fetch(`${API_BASE}/cases`);
  if (!res.ok) throw new Error("Failed to fetch cases");
  const data = await res.json();
  return data.cases;
}

export async function getCase(caseId: string): Promise<CaseDetail> {
  const res = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!res.ok) throw new Error(`Failed to fetch case ${caseId}`);
  return res.json();
}

export async function approveCase(
  caseId: string,
  feedback?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback }),
  });
  if (!res.ok) throw new Error("Approval failed");
}

export async function rejectCase(
  caseId: string,
  feedback?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback }),
  });
  if (!res.ok) throw new Error("Rejection failed");
}

export async function getAuditTrail(caseId: string): Promise<AuditTrail> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/audit`);
  if (!res.ok) throw new Error("Failed to fetch audit trail");
  return res.json();
}

export async function verifyAuditTrail(
  caseId: string
): Promise<AuditVerification> {
  const res = await fetch(`${API_BASE}/cases/${caseId}/audit/verify`);
  if (!res.ok) throw new Error("Failed to verify audit trail");
  return res.json();
}
