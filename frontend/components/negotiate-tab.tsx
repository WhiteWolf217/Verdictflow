/**
 * VerdictFlow — Negotiation Simulator
 * Interactive chat-based negotiation training with AI counterparty.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import {
  startSimulation,
  sendSimulationTurn,
  evaluateNegotiation,
  getNegotiationCoaching,
  getNegotiationEmail,
  type NegotiationStrategy,
  type NegotiationEvaluation,
  type CaseDetail,
} from "@/lib/api";
import RiskRadar from "@/components/risk-radar";

const SKILL_KEY = "vf_negotiation_scores";

interface SpeechRecResult {
  transcript: string;
}

interface SpeechRecResultList extends ArrayLike<SpeechRecResult> {
  isFinal: boolean;
}

interface SpeechRecLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: (e: { results: ArrayLike<SpeechRecResultList> }) => void;
  onend: () => void;
  onerror: () => void;
  start: () => void;
  stop: () => void;
}

const DIMENSIONS: { key: keyof NonNullable<NegotiationEvaluation["dimension_scores"]>; label: string }[] = [
  { key: "assertiveness", label: "Assertive" },
  { key: "preparation", label: "Prep" },
  { key: "communication", label: "Comms" },
  { key: "value_creation", label: "Value" },
  { key: "composure", label: "Composure" },
  { key: "closing", label: "Closing" },
];

interface NegotiateTabProps {
  caseData: CaseDetail;
}

type ChatMessage = {
  role: "user" | "counterparty" | "system";
  message: string;
};

const DIFFICULTY_CONFIG = {
  easy: { label: "Easy", desc: "Agreeable counterparty", color: "text-emerald-400", bg: "bg-emerald-400/10" },
  medium: { label: "Medium", desc: "Professional negotiator", color: "text-amber-400", bg: "bg-amber-400/10" },
  hard: { label: "Hard", desc: "Tough pressure tactics", color: "text-red-400", bg: "bg-red-400/10" },
};

export default function NegotiateTab({ caseData }: NegotiateTabProps) {
  const [mode, setMode] = useState<"coach" | "simulate">("coach");
  const [strategies, setStrategies] = useState<NegotiationStrategy[]>([]);
  const [isLoadingCoach, setIsLoadingCoach] = useState(false);

  // Simulator state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState("medium");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [canEvaluate, setCanEvaluate] = useState(false);
  const [evaluation, setEvaluation] = useState<NegotiationEvaluation | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  // Email drafter
  const [email, setEmail] = useState<string | null>(null);
  const [isDraftingEmail, setIsDraftingEmail] = useState(false);

  // Voice
  const [voiceOn, setVoiceOn] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecLike | null>(null);
  const baseTextRef = useRef("");

  // Skill history (persisted locally)
  const [history, setHistory] = useState<number[]>([]);
  useEffect(() => {
    try {
      const raw = localStorage.getItem(SKILL_KEY);
      if (raw) setHistory(JSON.parse(raw));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages.length]);

  const speak = (text: string) => {
    if (!voiceOn || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    try {
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.05;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } catch { /* ignore */ }
  };

  const toggleListen = () => {
    const w = window as unknown as {
      SpeechRecognition?: new () => SpeechRecLike;
      webkitSpeechRecognition?: new () => SpeechRecLike;
    };
    const SR = (typeof window !== "undefined" && (w.SpeechRecognition || w.webkitSpeechRecognition)) || null;
    if (!SR) {
      alert("Voice input isn't supported in this browser. Try Chrome or Edge.");
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }
    const rec = new SR();
    rec.lang = "en-US";
    rec.interimResults = true;
    try { rec.continuous = true; } catch { /* some browsers don't support continuous */ }

    // Capture what's already in the input field
    baseTextRef.current = input;

    rec.onresult = (e) => {
      let interim = "";
      let finalText = "";
      for (let i = 0; i < e.results.length; i++) {
        const result = e.results[i];
        const transcript = result[0].transcript;
        if (result.isFinal) {
          finalText += transcript;
        } else {
          interim += transcript;
        }
      }
      // Show committed text + final transcription + live interim
      const base = baseTextRef.current;
      const combined = (base ? base + " " : "") + finalText + interim;
      setInput(combined);
    };
    rec.onend = () => setIsListening(false);
    rec.onerror = () => setIsListening(false);
    recognitionRef.current = rec;
    setIsListening(true);
    rec.start();
  };

  const handleDraftEmail = async () => {
    setIsDraftingEmail(true);
    try {
      setEmail(await getNegotiationEmail(caseData.case_id));
    } catch {
      setEmail("Could not draft the email right now. Please try again.");
    }
    setIsDraftingEmail(false);
  };

  const handleLoadCoaching = async () => {
    setIsLoadingCoach(true);
    try {
      const findings = caseData.clause_findings.map((f) => ({
        category: f.category,
        risk_level: f.risk_level,
        explanation: f.explanation,
      }));
      const strats = await getNegotiationCoaching(caseData.case_id, findings);
      setStrategies(strats);
    } catch (e) {
      console.error(e);
    }
    setIsLoadingCoach(false);
  };

  const handleStartSimulation = async () => {
    setIsStarting(true);
    setEvaluation(null);
    setMessages([]);
    setCanEvaluate(false);

    const context = caseData.clause_findings
      .slice(0, 5)
      .map((f) => `[${f.risk_level}] ${f.category}: ${f.explanation}`)
      .join("\n");

    const parties = caseData.contract?.parties || [];
    const userRole = parties[0] || "buyer";
    const counterpartyRole = parties[1] || "seller";

    try {
      const session = await startSimulation(
        caseData.case_id,
        userRole,
        counterpartyRole,
        `Negotiating terms of ${caseData.contract?.doc_type || "contract"}: ${caseData.contract?.filename || "document"}`,
        context,
        difficulty
      );
      setSessionId(session.session_id);
      setMessages([
        { role: "system", message: `Simulation started. You are the ${userRole}. Negotiating with the ${session.counterparty_role}. Difficulty: ${difficulty}.` },
        { role: "counterparty", message: session.opening_message },
      ]);
    } catch (e) {
      console.error(e);
      setMessages([{ role: "system", message: "Failed to start simulation. Check backend connection." }]);
    }
    setIsStarting(false);
  };

  const handleSendMessage = async () => {
    if (!input.trim() || !sessionId || isSending) return;
    const msg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", message: msg }]);
    setIsSending(true);

    try {
      const result = await sendSimulationTurn(sessionId, msg);
      setMessages((prev) => [...prev, { role: "counterparty", message: result.counterparty_response }]);
      setCanEvaluate(result.can_evaluate);
      speak(result.counterparty_response);
    } catch (e) {
      console.error(e);
      setMessages((prev) => [...prev, { role: "system", message: "Failed to get response." }]);
    }
    setIsSending(false);
  };

  const handleEvaluate = async () => {
    if (!sessionId) return;
    setIsEvaluating(true);
    try {
      const result = await evaluateNegotiation(sessionId);
      setEvaluation(result.evaluation);
      setSessionId(null);
      // Persist the score for skill-progress tracking.
      try {
        const next = [...history, result.evaluation.overall_score].slice(-12);
        setHistory(next);
        localStorage.setItem(SKILL_KEY, JSON.stringify(next));
      } catch { /* ignore */ }
    } catch (e) {
      console.error(e);
    }
    setIsEvaluating(false);
  };

  const PRIORITY_COLOR: Record<string, string> = {
    must_win: "text-red-400 bg-red-400/10",
    important: "text-amber-400 bg-amber-400/10",
    nice_to_have: "text-blue-400 bg-blue-400/10",
  };

  return (
    <div className="space-y-6">
      {/* Mode tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setMode("coach")}
          className={`px-4 py-2 rounded-lg text-[12px] font-medium transition-all ${
            mode === "coach" ? "bg-blue-500/15 text-blue-400 border border-blue-500/30" : "text-zinc-500 hover:text-zinc-300 border border-transparent"
          }`}
        >
          Negotiation Coach
        </button>
        <button
          onClick={() => setMode("simulate")}
          className={`px-4 py-2 rounded-lg text-[12px] font-medium transition-all ${
            mode === "simulate" ? "bg-violet-500/15 text-violet-400 border border-violet-500/30" : "text-zinc-500 hover:text-zinc-300 border border-transparent"
          }`}
        >
          Live Simulator
        </button>
      </div>

      {/* ═══ COACH MODE ═══ */}
      {mode === "coach" && (
        <div className="space-y-4">
          {/* Negotiation email drafter */}
          <div className="surface-1 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[13px] text-zinc-200 font-medium">Draft the counterparty email</p>
                <p className="text-[11px] text-zinc-500">Turn the findings into a ready-to-send negotiation email.</p>
              </div>
              <button onClick={handleDraftEmail} disabled={isDraftingEmail} className="btn-outline whitespace-nowrap">
                {isDraftingEmail ? "Drafting…" : "Draft Email"}
              </button>
            </div>
            {email && (
              <div className="mt-3 pt-3 border-t border-zinc-800/40">
                <pre className="text-[11px] text-zinc-300 whitespace-pre-wrap font-sans leading-relaxed max-h-64 overflow-y-auto">{email}</pre>
                <button
                  onClick={() => { navigator.clipboard?.writeText(email); }}
                  className="btn-outline mt-2 text-[11px]"
                >
                  Copy email
                </button>
              </div>
            )}
          </div>

          {strategies.length === 0 ? (
            <div className="surface-1 p-8 text-center">
              <svg className="w-10 h-10 text-zinc-700 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
              </svg>
              <p className="text-[13px] text-zinc-400 mb-1">AI Negotiation Coach</p>
              <p className="text-[11px] text-zinc-600 mb-4">Generate strategies for each finding in your contract</p>
              <button
                onClick={handleLoadCoaching}
                disabled={isLoadingCoach || caseData.clause_findings.length === 0}
                className="btn-primary"
              >
                {isLoadingCoach ? "Analyzing..." : "Generate Strategies"}
              </button>
            </div>
          ) : (
            <div className="space-y-3 stagger">
              {strategies.map((s, i) => (
                <div key={i} className="surface-1 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[12px] text-zinc-300 font-medium">{s.finding.slice(0, 80)}{s.finding.length > 80 ? "..." : ""}</p>
                    <span className={`badge ${PRIORITY_COLOR[s.priority] || "text-zinc-400 bg-zinc-400/10"}`}>
                      {s.priority?.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-[12px] text-zinc-500 leading-relaxed mb-3">{s.strategy}</p>

                  {/* Talking points */}
                  <div className="mb-2.5">
                    <p className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider mb-1.5">Talking Points</p>
                    <div className="space-y-1">
                      {s.talking_points?.map((tp, j) => (
                        <p key={j} className="text-[11px] text-blue-400/80 pl-3 border-l-2 border-blue-500/20">
                          &ldquo;{tp}&rdquo;
                        </p>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider mb-1">Leverage</p>
                      <p className="text-[11px] text-emerald-400/70">{s.leverage}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider mb-1">Fallback</p>
                      <p className="text-[11px] text-amber-400/70">{s.fallback}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══ SIMULATOR MODE ═══ */}
      {mode === "simulate" && (
        <div>
          {/* No active session — show start panel */}
          {!sessionId && !evaluation && (
            <div className="surface-1 p-6">
              <h3 className="text-[14px] font-semibold text-zinc-200 mb-1">Negotiation Simulator</h3>
              <p className="text-[12px] text-zinc-500 mb-5">
                Practice negotiating this contract with an AI counterparty. Get scored on your technique.
              </p>

              {/* Difficulty selector */}
              <p className="text-[10px] text-zinc-600 font-medium uppercase tracking-wider mb-2">Difficulty</p>
              <div className="flex gap-2 mb-5">
                {Object.entries(DIFFICULTY_CONFIG).map(([key, config]) => (
                  <button
                    key={key}
                    onClick={() => setDifficulty(key)}
                    className={`px-3 py-2 rounded-lg text-[11px] font-medium border transition-all ${
                      difficulty === key
                        ? `${config.bg} ${config.color} border-current`
                        : "text-zinc-500 border-zinc-800 hover:border-zinc-600"
                    }`}
                  >
                    <span className="block">{config.label}</span>
                    <span className="block text-[9px] opacity-60 mt-0.5">{config.desc}</span>
                  </button>
                ))}
              </div>

              <button onClick={handleStartSimulation} disabled={isStarting} className="btn-primary w-full">
                {isStarting ? "Setting up..." : "Start Simulation"}
              </button>
            </div>
          )}

          {/* Active session — chat interface */}
          {sessionId && (
            <div className="surface-1 overflow-hidden flex flex-col" style={{ height: 450 }}>
              {/* Chat messages */}
              <div ref={chatRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    {msg.role === "system" ? (
                      <div className="w-full text-center py-2">
                        <span className="text-[10px] text-zinc-600 bg-zinc-800/50 px-3 py-1 rounded-full">{msg.message}</span>
                      </div>
                    ) : (
                      <div className={`max-w-[75%] px-3.5 py-2.5 rounded-xl ${
                        msg.role === "user"
                          ? "bg-blue-500/15 text-blue-100 rounded-br-sm"
                          : "bg-zinc-800/60 text-zinc-300 rounded-bl-sm"
                      }`}>
                        <p className="text-[10px] font-medium mb-1 opacity-50">
                          {msg.role === "user" ? "You" : "Counterparty"}
                        </p>
                        <p className="text-[12px] leading-relaxed">{msg.message}</p>
                      </div>
                    )}
                  </div>
                ))}

                {isSending && (
                  <div className="flex justify-start">
                    <div className="bg-zinc-800/60 px-3.5 py-2.5 rounded-xl rounded-bl-sm">
                      <div className="flex gap-1 py-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0s" }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0.15s" }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0.3s" }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Input bar */}
              <div className="border-t border-zinc-800/50 p-3 flex gap-2 items-center">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                  placeholder="Type your negotiation response..."
                  className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-[12px] text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
                  disabled={isSending}
                  id="negotiate-input"
                />
                <button
                  onClick={toggleListen}
                  title="Speak your response"
                  className={`px-3 rounded-lg border transition-all ${
                    isListening ? "border-red-500/50 text-red-400 bg-red-500/10 animate-pulse" : "border-zinc-700 text-zinc-400 hover:border-zinc-500"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                  </svg>
                </button>
                <button
                  onClick={() => setVoiceOn((v) => !v)}
                  title="Toggle spoken replies"
                  className={`px-3 rounded-lg border transition-all ${
                    voiceOn ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10" : "border-zinc-700 text-zinc-500 hover:border-zinc-500"
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
                  </svg>
                </button>
                <button onClick={handleSendMessage} disabled={isSending || !input.trim()} className="btn-primary px-4">
                  Send
                </button>
                {canEvaluate && (
                  <button onClick={handleEvaluate} disabled={isEvaluating} className="btn-outline px-3 whitespace-nowrap">
                    {isEvaluating ? "..." : "End & Score"}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Evaluation results */}
          {evaluation && (
            <div className="space-y-4 animate-scale-in">
              {/* Score card */}
              <div className="surface-1 p-6 text-center">
                <div className="inline-flex items-baseline gap-2 mb-2">
                  <span className="text-5xl font-bold text-zinc-100">{evaluation.overall_score}</span>
                  <span className="text-lg text-zinc-500">/100</span>
                </div>
                <div className="mb-3">
                  <span className={`badge text-lg px-4 py-1.5 ${
                    evaluation.overall_score >= 80 ? "bg-emerald-400/10 text-emerald-400" :
                    evaluation.overall_score >= 60 ? "bg-amber-400/10 text-amber-400" :
                    "bg-red-400/10 text-red-400"
                  }`}>
                    {evaluation.letter_grade}
                  </span>
                </div>
                <p className="text-[13px] text-zinc-400 max-w-md mx-auto">{evaluation.summary}</p>
              </div>

              {/* Performance breakdown — radar + per-dimension bars */}
              {evaluation.dimension_scores && (
                <div className="surface-1 p-5">
                  <p className="metric-label mb-4">Performance Breakdown</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                    {/* Radar */}
                    <div className="flex justify-center">
                      <RiskRadar
                        size={200}
                        data={DIMENSIONS.map((d) => ({
                          label: d.label,
                          value: Math.max(0, Math.min(1, (evaluation.dimension_scores?.[d.key] ?? 0) / 100)),
                        }))}
                      />
                    </div>
                    {/* Bars */}
                    <div className="space-y-2.5">
                      {DIMENSIONS.map((d) => {
                        const v = evaluation.dimension_scores?.[d.key] ?? 0;
                        const color = v >= 75 ? "bg-emerald-400" : v >= 50 ? "bg-amber-400" : "bg-red-400";
                        return (
                          <div key={d.key}>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[11px] text-zinc-400">{d.label}</span>
                              <span className="text-[11px] text-zinc-300 font-medium font-mono">{v}</span>
                            </div>
                            <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                              <div
                                className={`h-full rounded-full ${color} transition-all duration-700 ease-out`}
                                style={{ width: `${Math.max(0, Math.min(100, v))}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* Details grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="surface-1 p-4">
                  <p className="metric-label mb-2">Strengths</p>
                  <ul className="space-y-1.5">
                    {evaluation.strengths.map((s, i) => (
                      <li key={i} className="text-[12px] text-emerald-400/80 flex items-start gap-2">
                        <span className="shrink-0 mt-0.5">+</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="surface-1 p-4">
                  <p className="metric-label mb-2">Areas to Improve</p>
                  <ul className="space-y-1.5">
                    {evaluation.improvements.map((s, i) => (
                      <li key={i} className="text-[12px] text-amber-400/80 flex items-start gap-2">
                        <span className="shrink-0 mt-0.5">→</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="surface-1 p-4">
                  <p className="metric-label mb-2">Tactics Detected</p>
                  <div className="flex flex-wrap gap-1.5">
                    {evaluation.tactics_used.map((t, i) => (
                      <span key={i} className="badge bg-blue-400/10 text-blue-400">{t}</span>
                    ))}
                  </div>
                </div>
                <div className="surface-1 p-4">
                  <p className="metric-label mb-2">Missed Opportunities</p>
                  <ul className="space-y-1.5">
                    {evaluation.missed_opportunities.map((s, i) => (
                      <li key={i} className="text-[12px] text-zinc-500 flex items-start gap-2">
                        <span className="shrink-0 mt-0.5">!</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Skill progress over time */}
              {history.length > 1 && (
                <div className="surface-1 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <p className="metric-label">Your Skill Progress</p>
                    <span className="text-[11px] text-zinc-500">
                      best {Math.max(...history)} · avg {Math.round(history.reduce((a, b) => a + b, 0) / history.length)}
                    </span>
                  </div>
                  <div className="flex items-end gap-1.5 h-20">
                    {history.map((sc, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center justify-end h-full" title={`Session ${i + 1}: ${sc}`}>
                        <div
                          className={`w-full rounded-t ${sc >= 80 ? "bg-emerald-400/70" : sc >= 60 ? "bg-amber-400/70" : "bg-red-400/70"} ${i === history.length - 1 ? "ring-1 ring-white/30" : ""}`}
                          style={{ height: `${Math.max(6, sc)}%` }}
                        />
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] text-zinc-600 mt-2 text-center">{history.length} sessions tracked on this device</p>
                </div>
              )}

              <button onClick={() => { setEvaluation(null); setMessages([]); }} className="btn-outline w-full">
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
