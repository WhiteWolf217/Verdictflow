/**
 * VerdictFlow — Money-at-Stake Hero
 * Bold, animated count-up of total financial exposure. Makes risk visceral.
 */

"use client";

import { useEffect, useState } from "react";

export default function MoneyHero({ amount, findings }: { amount: number; findings: number }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (amount <= 0) {
      setDisplay(0);
      return;
    }
    const duration = 900;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(amount * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [amount]);

  return (
    <div className="surface-1 p-6 mb-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-amber-500/5 to-transparent pointer-events-none" />
      <div className="relative flex items-center justify-between flex-wrap gap-4">
        <div>
          <p className="text-[11px] text-zinc-500 font-medium uppercase tracking-wider mb-1">Total Financial Exposure at Risk</p>
          <p className="text-[40px] leading-none font-bold text-amber-400 tabular-nums">
            ${display.toLocaleString()}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[28px] leading-none font-bold text-zinc-200">{findings}</p>
          <p className="text-[11px] text-zinc-500 mt-1">risks identified across 6 agents</p>
        </div>
      </div>
    </div>
  );
}
