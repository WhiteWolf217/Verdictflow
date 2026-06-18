/**
 * VerdictFlow — Risk Score Gauge
 * Animated circular SVG gauge showing 0-100 risk score.
 */

"use client";

import { useEffect, useState } from "react";

interface RiskGaugeProps {
  score: number; // 0-100
  size?: number;
}

export default function RiskGauge({ score, size = 160 }: RiskGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (animatedScore / 100) * circumference;
  const center = size / 2;

  // Color based on score
  const getColor = (s: number) => {
    if (s <= 30) return { stroke: "#22c55e", text: "text-emerald-400", label: "Low Risk", bg: "bg-emerald-400/10" };
    if (s <= 60) return { stroke: "#f59e0b", text: "text-amber-400", label: "Medium Risk", bg: "bg-amber-400/10" };
    if (s <= 80) return { stroke: "#f97316", text: "text-orange-400", label: "High Risk", bg: "bg-orange-400/10" };
    return { stroke: "#ef4444", text: "text-red-400", label: "Critical Risk", bg: "bg-red-400/10" };
  };

  const color = getColor(animatedScore);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="transform -rotate-90"
        >
          {/* Background ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.04)"
            strokeWidth="8"
          />
          {/* Progress ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color.stroke}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              transition: "stroke-dashoffset 1.2s ease-out, stroke 0.5s ease",
            }}
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold tracking-tight ${color.text}`}>
            {Math.round(animatedScore)}
          </span>
          <span className="text-[10px] text-zinc-600 uppercase tracking-wider font-medium mt-0.5">
            Risk Score
          </span>
        </div>
      </div>

      <span className={`badge ${color.bg} ${color.text}`}>
        {color.label}
      </span>
    </div>
  );
}
