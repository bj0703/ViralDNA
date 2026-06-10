import { useEffect, useRef, useCallback, useState } from 'react';
import type { SSEEventPayload } from '../types';

interface UseSSEEventSourceOptions {
  jobId: string | null;
  onEvent?: (event: SSEEventPayload) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onFallbackPollStart?: () => void;
  pollIntervalMs?: number;
}

export function useSSEEventSource({
  jobId,
  onEvent,
  onConnect,
  onDisconnect,
  onFallbackPollStart,
  pollIntervalMs = 1500,
}: UseSSEEventSourceOptions) {
  const esRef = useRef<EventSource | null>(null);
  const lastEventOffsetRef = useRef<number>(0);
  const reconnectDelayRef = useRef<number>(1000);
  const pollTimerRef = useRef<number | null>(null);
  const usingFallbackPollRef = useRef<boolean>(false);
  const connectedRef = useRef<boolean>(false);
  const prevJobIdRef = useRef<string | null>(null);
  const connectDebounceTimerRef = useRef<number | null>(null);

  const [isConnectedRaw, setIsConnectedRaw] = useState(false);
  const [isFallbackPolling, setIsFallbackPolling] = useState(false);
  const [lastEventOffset, setLastEventOffset] = useState<number>(0);

  // UI层300ms防抖：连接状态稳定满300ms才对外展示绿色状态，绝对不会出现肉眼可见闪烁
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (isConnectedRaw === isConnected) return;
    if (connectDebounceTimerRef.current) {
      window.clearTimeout(connectDebounceTimerRef.current);
    }
    if (isConnectedRaw) {
      connectDebounceTimerRef.current = window.setTimeout(() => {
        setIsConnected(true);
      }, 300);
    } else {
      setIsConnected(false);
    }
    return () => {
      if (connectDebounceTimerRef.current) {
        window.clearTimeout(connectDebounceTimerRef.current);
      }
    };
  }, [isConnectedRaw, isConnected]);

  const closeConnection = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (connectDebounceTimerRef.current) {
      window.clearTimeout(connectDebounceTimerRef.current);
      connectDebounceTimerRef.current = null;
    }
    if (connectedRef.current) {
      connectedRef.current = false;
      setIsConnectedRaw(false);
      onDisconnect?.();
    }
  }, [onDisconnect]);

  const startFallbackPoll = useCallback(() => {
    usingFallbackPollRef.current = true;
    setIsFallbackPolling(true);
    if (onFallbackPollStart) {
      onFallbackPollStart();
    }
    pollTimerRef.current = window.setInterval(async () => {
      if (!jobId) return;
      try {
        const url = `/api/orchestration/jobs/${jobId}/trace`;
        const res = await fetch(url);
        const data = await res.json();
        const allEvents = (data?.event_log ?? []) as SSEEventPayload[];
        const newEvents = allEvents.slice(lastEventOffsetRef.current);
        for (const evt of newEvents) {
          if (onEvent) {
            onEvent(evt);
          }
          lastEventOffsetRef.current += 1;
          setLastEventOffset(lastEventOffsetRef.current);
        }
      } catch (e) {
        console.warn('[SSE Fallback Poll] 请求失败:', e);
      }
    }, pollIntervalMs);
  }, [jobId, onEvent, onFallbackPollStart, pollIntervalMs]);

  const connect = useCallback(() => {
    if (!jobId) return;
    closeConnection();

    if (prevJobIdRef.current !== jobId) {
      usingFallbackPollRef.current = false;
      setIsFallbackPolling(false);
      lastEventOffsetRef.current = 0;
      setLastEventOffset(0);
      prevJobIdRef.current = jobId;
      reconnectDelayRef.current = 1000;
    }
    if (usingFallbackPollRef.current) return;

    try {
      const esUrl = `/api/orchestration/jobs/${jobId}/stream?last_event_id=${lastEventOffsetRef.current}`;
      const es = new EventSource(esUrl);
      esRef.current = es;

      es.onmessage = (msg) => {
        if (msg.data.startsWith(':')) {
          return;
        }
        try {
          const parsed: SSEEventPayload = JSON.parse(msg.data);
          if (onEvent) {
            onEvent(parsed);
          }
          lastEventOffsetRef.current += 1;
          setLastEventOffset(lastEventOffsetRef.current);
          reconnectDelayRef.current = 1000;
        } catch (e) {
          console.warn('[SSE] 解析事件失败:', e, msg.data);
        }
      };

      es.onerror = () => {
        es.close();
        if (reconnectDelayRef.current > 8000) {
          console.warn('[SSE] 重连次数过多，切换到轮询降级模式');
          startFallbackPoll();
          return;
        }
        setTimeout(() => connect(), reconnectDelayRef.current);
        reconnectDelayRef.current *= 2;
      };

      es.onopen = () => {
        reconnectDelayRef.current = 1000;
        if (!connectedRef.current) {
          connectedRef.current = true;
          setIsConnectedRaw(true);
          onConnect?.();
        }
        if (usingFallbackPollRef.current) {
          console.log('[SSE] 连接恢复，停止轮询降级');
          usingFallbackPollRef.current = false;
          setIsFallbackPolling(false);
          if (pollTimerRef.current !== null) {
            window.clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
        }
      };
    } catch (e) {
      console.warn('[SSE] EventSource 初始化失败，切换轮询降级模式:', e);
      startFallbackPoll();
    }
  }, [jobId, onEvent, closeConnection, startFallbackPoll, onConnect]);

  useEffect(() => {
    if (jobId) {
      connect();
    } else {
      closeConnection();
      lastEventOffsetRef.current = 0;
      setLastEventOffset(0);
      usingFallbackPollRef.current = false;
      setIsFallbackPolling(false);
      prevJobIdRef.current = null;
      reconnectDelayRef.current = 1000;
    }
    return () => closeConnection();
  }, [jobId, connect, closeConnection]);

  return {
    isConnected,
    isFallbackPolling,
    lastEventOffset,
    close: closeConnection,
  };
}
