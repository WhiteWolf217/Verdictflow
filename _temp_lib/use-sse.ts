/**
 * VerdictFlow — SSE Hook
 *
 * Custom React hook for Server-Sent Events.
 * Connects to the backend SSE stream for real-time case progress updates.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface SSEEvent {
  event_type: string;
  case_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

interface UseSSEOptions {
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** Maximum reconnect attempts (default: 10) */
  maxReconnects?: number;
}

interface UseSSEReturn {
  /** All events received */
  events: SSEEvent[];
  /** Latest event */
  latestEvent: SSEEvent | null;
  /** Connection status */
  isConnected: boolean;
  /** Whether we're attempting to reconnect */
  isReconnecting: boolean;
  /** Error message if any */
  error: string | null;
  /** Manually connect */
  connect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
}

export function useSSE(
  caseId: string | null,
  options: UseSSEOptions = {}
): UseSSEReturn {
  const {
    autoConnect = true,
    reconnectDelay = 3000,
    maxReconnects = 10,
  } = options;

  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [latestEvent, setLatestEvent] = useState<SSEEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    setIsReconnecting(false);
  }, []);

  const connect = useCallback(() => {
    if (!caseId) return;

    // Clean up existing connection
    disconnect();

    const url = `${API_BASE}/cases/${caseId}/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setIsReconnecting(false);
      setError(null);
      reconnectCountRef.current = 0;
    };

    eventSource.onmessage = (event) => {
      try {
        const parsed: SSEEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, parsed]);
        setLatestEvent(parsed);

        // Auto-disconnect on terminal events
        if (
          parsed.event_type === "case_finalized" ||
          parsed.event_type === "case_error"
        ) {
          setTimeout(() => disconnect(), 1000);
        }
      } catch (e) {
        // Ignore parse errors (keepalive pings, etc.)
      }
    };

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();

      if (reconnectCountRef.current < maxReconnects) {
        setIsReconnecting(true);
        reconnectCountRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, reconnectDelay);
      } else {
        setError("Connection lost. Max reconnect attempts reached.");
        setIsReconnecting(false);
      }
    };
  }, [caseId, disconnect, maxReconnects, reconnectDelay]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect && caseId) {
      connect();
    }
    return () => disconnect();
  }, [caseId, autoConnect, connect, disconnect]);

  return {
    events,
    latestEvent,
    isConnected,
    isReconnecting,
    error,
    connect,
    disconnect,
  };
}
