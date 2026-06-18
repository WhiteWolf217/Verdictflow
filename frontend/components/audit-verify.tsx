/**
 * VerdictFlow — Tamper-Evident Verification Showcase
 * Live re-verification of the SHA-256 hash chain, plus a one-click tamper demo
 * that proves any alteration is cryptographically detected.
 */

"use client";

import { useState } from "react";
import { verifyAuditTrail, verifyAuditTrailTamper, type TamperVerification } from "@/lib/api";

type Result = { kind: "verified" | "tamper"; data: TamperVerification } | null;

export default function AuditVerify({ caseId, latestHash }: { caseId: string; latestHash?: string | null }) {
  const [result, setResult] = useState<Result>(null);
  const [busy, setBusy] = useState<"verify" | "tamper" | null>(null);

  const doVerify = async () => {
    setBusy("verify");
    setResult(null);
    try {
      const data = await verifyAuditTrail(caseId);
      setResult({ kind: "verified", data });
    } catch { /* ignore */ }
    setBusy(null);
  };

  const doTamper = async () => {
    setBusy("tamper");
    setResult(null);
    try {
      const data = await verifyAuditTrailTamper(caseId);
      setResult({ kind: "tamper", data });
    } catch { /* ignore */ }
    setBusy(null);
  };

  const valid = result?.data.is_valid;

  return (
    <div className="surface-1 p-5">
      <div className="flex items-center justify-between mb-1">
        <p className="metric-label">Tamper-Evident Provenance</p>
        <span className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded font-mono">SHA-256</span>
      </div>
      <p className="text-[12px] text-zinc-500 mb-4">
        Every agent action is hash-chained. Verify the seal, or simulate tampering to see it break.
      </p>

      <div className="flex gap-2 mb-4">
        <button onClick={doVerify} disabled={busy !== null} className="btn-primary">
          {busy === "verify" ? "Verifying…" : "Verify Integrity"}
        </button>
        <button onClick={doTamper} disabled={busy !== null} className="btn-outline">
          {busy === "tamper" ? "Simulating…" : "Simulate Tamper"}
        </button>
      </div>

      {result && (
        <div
          className={`rounded-lg border p-4 animate-scale-in ${
            valid ? "border-emerald-500/30 bg-emerald-500/5" : "border-red-500/30 bg-red-500/5"
          }`}
        >
          <div className="flex items-center gap-2 mb-1.5">
            {valid ? (
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            )}
            <span className={`text-[13px] font-semibold ${valid ? "text-emerald-400" : "text-red-400"}`}>
              {valid
                ? `Integrity verified · ${result.data.chain_length}/${result.data.chain_length} entries intact`
                : "Tampering detected — chain broken"}
            </span>
          </div>
          {result.kind === "tamper" && !valid && (
            <p className="text-[11px] text-red-400/80 mb-1">
              Altered entry #{result.data.tampered_step}: {result.data.error}
            </p>
          )}
          {result.kind === "tamper" && (
            <p className="text-[10px] text-zinc-600">
              (Simulation only — the real sealed chain was not modified.)
            </p>
          )}
          {latestHash && (
            <p className="text-[10px] text-zinc-600 font-mono mt-2 truncate" title={latestHash}>
              seal: {latestHash.slice(0, 32)}…
            </p>
          )}
        </div>
      )}
    </div>
  );
}
