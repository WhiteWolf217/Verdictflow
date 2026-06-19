/**
 * VerdictFlow — API Client
 * All backend fetch wrappers and TypeScript types.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ───────────────────────────────────────────────────────────────────

export interface CaseListItem {
  case_id: string;
  filename: string;
  status: string;
  doc_type: string;
  created_at: string;
  total_findings: number;
}

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
  risk_level: string;
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
  severity: string;
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
  status: string;
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
  priority: string;
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
  clause_risks: { low: number; medium: number; high: number; critical: number };
  attack_severities: { low: number; medium: number; high: number; critical: number };
  compliance_status: { compliant: number; non_compliant: number; needs_review: number };
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
  verdict: string | null;
  verdict_recommendation: string | null;
  confidence_score: number;
  human_approval: HumanApproval | null;
  risk_summary: RiskSummary;
  band_room_id: string | null;
  created_at: string;
  finalized_at: string | null;
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

export interface DebateRound {
  speaker: string;
  message: string;
  stance: string;
}

export interface TamperVerification {
  case_id: string;
  is_valid: boolean;
  chain_length: number;
  latest_hash: string | null;
  error: string | null;
  simulated?: boolean;
  tampered_step?: number | null;
}

export interface NegotiationStrategy {
  finding: string;
  strategy: string;
  talking_points: string[];
  leverage: string;
  fallback: string;
  priority: string;
}

export interface NegotiationEvaluation {
  overall_score: number;
  dimension_scores?: {
    assertiveness: number;
    preparation: number;
    communication: number;
    value_creation: number;
    composure: number;
    closing: number;
  };
  strengths: string[];
  improvements: string[];
  tactics_used: string[];
  missed_opportunities: string[];
  letter_grade: string;
  summary: string;
}

export interface BandRoom {
  room_id: string;
  url: string | null;
  mode: string;
  agent_chats: Record<string, string>;
  name: string;
  case_id: string | null;
  messages: { agent: string; message: string; timestamp: string }[];
  events: { event_type: string; payload: Record<string, unknown>; timestamp: string }[];
  created_at: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// ── Contract Upload ─────────────────────────────────────────────────────────

export async function uploadContract(file: File): Promise<{ case_id: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/contracts/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

// ── Cases ───────────────────────────────────────────────────────────────────

export async function listCases(): Promise<CaseListItem[]> {
  const data = await apiFetch<{ cases: CaseListItem[] }>("/api/cases");
  return data.cases;
}

export async function getCase(caseId: string): Promise<CaseDetail> {
  return apiFetch<CaseDetail>(`/api/cases/${caseId}`);
}

// ── Human Gate ──────────────────────────────────────────────────────────────

export async function approveCase(caseId: string, feedback?: string) {
  return apiFetch(`/api/cases/${caseId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback: feedback || null }),
  });
}

export async function rejectCase(caseId: string, feedback?: string) {
  return apiFetch(`/api/cases/${caseId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback: feedback || null }),
  });
}

// ── Audit ───────────────────────────────────────────────────────────────────

export async function getAuditTrail(caseId: string): Promise<{ audit_chain: AuditEntry[]; chain_length: number; latest_hash: string | null }> {
  return apiFetch(`/api/cases/${caseId}/audit`);
}

export async function verifyAuditTrail(caseId: string): Promise<TamperVerification> {
  return apiFetch(`/api/cases/${caseId}/audit/verify`);
}

export async function verifyAuditTrailTamper(caseId: string): Promise<TamperVerification> {
  return apiFetch(`/api/cases/${caseId}/audit/verify?simulate_tamper=true`);
}

// ── Downloads ───────────────────────────────────────────────────────────────

export async function downloadAudit(caseId: string) {
  const res = await fetch(`${API_BASE}/api/cases/${caseId}/download`);
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `verdictflow_audit_${caseId.slice(0, 8)}.docx`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadCounterDraft(caseId: string) {
  const res = await fetch(`${API_BASE}/api/cases/${caseId}/counter-draft`);
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `verdictflow_counter_draft_${caseId.slice(0, 8)}.docx`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── RAG Chat ────────────────────────────────────────────────────────────────

export async function askContract(caseId: string, question: string): Promise<{ answer: string; citations: string[] }> {
  return apiFetch(`/api/cases/${caseId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

// ── Agent Boardroom ─────────────────────────────────────────────────────────

export async function getAgentDebate(caseId: string): Promise<DebateRound[]> {
  const data = await apiFetch<{ rounds: DebateRound[] }>(`/api/cases/${caseId}/debate`, {
    method: "POST",
  });
  return data.rounds;
}

// ── Negotiation ─────────────────────────────────────────────────────────────

export async function getNegotiationCoaching(
  caseId: string,
  findings: { category: string; risk_level: string; explanation: string }[],
): Promise<NegotiationStrategy[]> {
  const data = await apiFetch<{ strategies: NegotiationStrategy[] }>("/api/negotiate/coach", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId, findings }),
  });
  return data.strategies;
}

export async function startSimulation(
  caseId: string,
  userRole: string,
  counterpartyRole: string,
  scenario: string,
  contractContext: string,
  difficulty: string,
): Promise<{ session_id: string; counterparty_role: string; opening_message: string; difficulty: string }> {
  return apiFetch("/api/negotiate/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      case_id: caseId,
      user_role: userRole,
      counterparty_role: counterpartyRole,
      scenario: scenario,
      contract_context: contractContext,
      difficulty,
    }),
  });
}

export async function sendSimulationTurn(
  sessionId: string,
  userMessage: string,
): Promise<{ session_id: string; counterparty_response: string; turn: number; can_evaluate: boolean }> {
  return apiFetch("/api/negotiate/turn", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, user_message: userMessage }),
  });
}

export async function evaluateNegotiation(
  sessionId: string,
): Promise<{ evaluation: NegotiationEvaluation }> {
  return apiFetch("/api/negotiate/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function getNegotiationEmail(caseId: string): Promise<string> {
  const data = await apiFetch<{ email: string }>(`/api/cases/${caseId}/negotiation-email`, {
    method: "POST",
  });
  return data.email;
}

// ── Band Room ───────────────────────────────────────────────────────────────

export async function getCaseRoom(caseId: string): Promise<BandRoom | null> {
  try {
    return await apiFetch<BandRoom>(`/api/cases/${caseId}/room`);
  } catch {
    return null;
  }
}
