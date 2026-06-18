/**
 * VerdictFlow — Risk Radar Chart
 * Pure SVG spider chart showing risk across 6 dimensions.
 */

"use client";

import { useEffect, useState } from "react";

interface RiskRadarProps {
  data: { label: string; value: number }[]; // 0-1 scale for each axis
  size?: number;
}

export default function RiskRadar({ data, size = 200 }: RiskRadarProps) {
  const [animated, setAnimated] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 200);
    return () => clearTimeout(t);
  }, []);

  const center = size / 2;
  const maxR = (size - 40) / 2;
  const levels = 4;
  const axes = data.length || 6;

  const angleStep = (2 * Math.PI) / axes;

  const getPoint = (index: number, value: number) => {
    const angle = angleStep * index - Math.PI / 2;
    return {
      x: center + maxR * value * Math.cos(angle),
      y: center + maxR * value * Math.sin(angle),
    };
  };

  // Build polygon path
  const polygonPoints = data
    .map((d, i) => {
      const v = animated ? d.value : 0;
      const pt = getPoint(i, v);
      return `${pt.x},${pt.y}`;
    })
    .join(" ");

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="overflow-visible">
        {/* Grid rings */}
        {Array.from({ length: levels }, (_, i) => {
          const r = ((i + 1) / levels) * maxR;
          const points = Array.from({ length: axes }, (_, j) => {
            const angle = angleStep * j - Math.PI / 2;
            return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
          }).join(" ");
          return (
            <polygon
              key={`ring-${i}`}
              points={points}
              fill="none"
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1"
            />
          );
        })}

        {/* Axis lines */}
        {data.map((_, i) => {
          const pt = getPoint(i, 1);
          return (
            <line
              key={`axis-${i}`}
              x1={center}
              y1={center}
              x2={pt.x}
              y2={pt.y}
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1"
            />
          );
        })}

        {/* Data polygon */}
        <polygon
          points={polygonPoints}
          fill="rgba(59, 130, 246, 0.12)"
          stroke="rgba(59, 130, 246, 0.6)"
          strokeWidth="1.5"
          style={{ transition: "all 1s ease-out" }}
        />

        {/* Data points */}
        {data.map((d, i) => {
          const v = animated ? d.value : 0;
          const pt = getPoint(i, v);
          return (
            <circle
              key={`dot-${i}`}
              cx={pt.x}
              cy={pt.y}
              r="3"
              fill="#3b82f6"
              stroke="rgba(9,9,11,0.8)"
              strokeWidth="2"
              style={{ transition: "all 1s ease-out" }}
            />
          );
        })}

        {/* Labels */}
        {data.map((d, i) => {
          const pt = getPoint(i, 1.2);
          return (
            <text
              key={`label-${i}`}
              x={pt.x}
              y={pt.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-zinc-500 text-[9px] font-medium"
            >
              {d.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
