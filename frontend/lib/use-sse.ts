/**
 * VerdictFlow — SSE Hook
 * Connects to the backend's Server-Sent Events stream for a case
 * and provides real-time event updates.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SSEEvent {
  event_type: string;
  case_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export function useSSE(caseId: string | undefined) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (!caseId) return;

    // Close any existing connection
    if (sourceRef.current) {
      sourceRef.current.close();
    }

    const url = `${API_BASE}/api/cases/${caseId}/stream`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => {
      setIsConnected(true);
    };

    source.onmessage = (e) => {
      try {
        const event: SSEEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);

        // Close on terminal events
        if (event.event_type === "case_finalized" || event.event_type === "case_error") {
          source.close();
          setIsConnected(false);
        }
      } catch {
        // Ignore parse errors (keepalive pings, etc.)
      }
    };

    source.onerror = () => {
      setIsConnected(false);
      source.close();
    };
  }, [caseId]);

  useEffect(() => {
    connect();
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close();
        setIsConnected(false);
      }
    };
  }, [connect]);

  return { events, isConnected };
}
