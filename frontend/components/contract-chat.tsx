/**
 * VerdictFlow — Ask-this-Contract Copilot
 * RAG-backed chat over the uploaded contract, with cited source excerpts.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { askContract } from "@/lib/api";

type Msg = { role: "user" | "assistant"; text: string; citations?: string[] };

const SUGGESTIONS = [
  "What is the termination notice period?",
  "Is there an auto-renewal clause?",
  "What are my liability limits?",
  "Summarize the payment terms.",
];

export default function ContractChat({ caseId }: { caseId: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length, isLoading]);

  const send = async (q: string) => {
    const question = q.trim();
    if (!question || isLoading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setIsLoading(true);
    try {
      const res = await askContract(caseId, question);
      setMessages((prev) => [...prev, { role: "assistant", text: res.answer, citations: res.citations }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Sorry — I couldn't answer that right now." }]);
    }
    setIsLoading(false);
  };

  return (
    <div className="surface-1 overflow-hidden flex flex-col" style={{ height: 520 }}>
      <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center gap-2 shrink-0">
        <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 3v-3z" />
        </svg>
        <span className="text-[13px] font-semibold text-zinc-200">Ask this Contract</span>
        <span className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded font-mono">RAG</span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <p className="text-[12px] text-zinc-500 mb-4">Ask anything about this contract — answers are grounded in the document.</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-md">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} className="text-[11px] text-blue-400/80 border border-blue-500/20 rounded-full px-3 py-1.5 hover:bg-blue-500/10 transition-colors">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] px-3.5 py-2.5 rounded-xl ${
              m.role === "user" ? "bg-blue-500/15 text-blue-100 rounded-br-sm" : "bg-zinc-800/60 text-zinc-300 rounded-bl-sm"
            }`}>
              <p className="text-[12px] leading-relaxed whitespace-pre-line">{m.text}</p>
              {m.citations && m.citations.length > 0 && (
                <div className="mt-2 pt-2 border-t border-zinc-700/40 space-y-1">
                  <p className="text-[9px] text-zinc-600 font-medium uppercase tracking-wider">Sources</p>
                  {m.citations.map((c, j) => (
                    <p key={j} className="text-[10px] text-zinc-500 italic leading-snug">&ldquo;{c.slice(0, 160)}…&rdquo;</p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800/60 px-3.5 py-2.5 rounded-xl rounded-bl-sm flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0.15s" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0.3s" }} />
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-zinc-800/50 p-3 flex gap-2 shrink-0">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          placeholder="Ask about termination, liability, payment terms…"
          className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-[12px] text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600"
          disabled={isLoading}
        />
        <button onClick={() => send(input)} disabled={isLoading || !input.trim()} className="btn-primary px-4">Ask</button>
      </div>
    </div>
  );
}
