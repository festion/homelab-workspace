import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketHook {
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastMessage: any;
  sendMessage: (message: any) => void;
  reconnect: () => void;
  disconnect: () => void;
  latency: number;
}

interface WebSocketOptions {
  reconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
  maxReconnectInterval?: number;
  heartbeatInterval?: number;
  onMessage?: (message: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: ErrorEvent | Error) => void;
}

export const useWebSocket = (url: string, options: WebSocketOptions = {}): WebSocketHook => {
  const {
    reconnect = true,
    maxReconnectAttempts = 10,
    reconnectInterval = 1000,
    maxReconnectInterval = 30000,
    heartbeatInterval = 30000,
    onMessage,
    onConnect,
    onDisconnect,
    onError
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [latency, setLatency] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  // Set when the consumer calls disconnect() so the close handler does not
  // schedule a reconnect for an intentional close (code 1000 is otherwise in
  // the retryable set). Reset on each connect().
  const intentionalClose = useRef(false);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutId = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutId = useRef<NodeJS.Timeout | null>(null);
  const pingStartTime = useRef<number>(0);
  const messageQueue = useRef<any[]>([]);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current);
      reconnectTimeoutId.current = null;
    }
  }, []);

  const clearHeartbeatTimeout = useCallback(() => {
    if (heartbeatTimeoutId.current) {
      clearInterval(heartbeatTimeoutId.current);
      heartbeatTimeoutId.current = null;
    }
  }, []);

  const sendHeartbeat = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      pingStartTime.current = Date.now();
      ws.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    clearHeartbeatTimeout();
    heartbeatTimeoutId.current = setInterval(sendHeartbeat, heartbeatInterval);
  }, [sendHeartbeat, heartbeatInterval, clearHeartbeatTimeout]);

  const processMessageQueue = useCallback(() => {
    while (messageQueue.current.length > 0 && ws.current?.readyState === WebSocket.OPEN) {
      const message = messageQueue.current.shift();
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  const connect = useCallback(() => {
    try {
      intentionalClose.current = false;
      setConnectionStatus('connecting');

      // Enhanced connection validation
      if (!url || typeof url !== 'string') {
        throw new Error('Invalid WebSocket URL provided');
      }

      // Check if WebSocket is supported
      if (typeof WebSocket === 'undefined') {
        throw new Error('WebSocket is not supported in this environment');
      }

      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        clearReconnectTimeout();
        startHeartbeat();
        processMessageQueue();
        onConnect?.();
      };

      ws.current.onmessage = (event) => {
        try {
          // Enhanced message validation
          if (!event.data) {
            console.warn('Received empty WebSocket message');
            return;
          }

          const message = JSON.parse(event.data);

          // Validate message structure
          if (typeof message !== 'object') {
            throw new Error('Invalid message format: not an object');
          }

          setLastMessage(message);

          if (message.type === 'pong') {
            const latency = Date.now() - pingStartTime.current;
            setLatency(latency);
          } else {
            onMessage?.(message);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          // Try to handle as raw text message
          if (typeof event.data === 'string') {
            setLastMessage({ type: 'raw', data: event.data });
            onMessage?.({ type: 'raw', data: event.data });
          }
        }
      };

      ws.current.onclose = (event) => {
        console.log(`WebSocket disconnected - Code: ${event.code}, Reason: ${event.reason}`);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        clearHeartbeatTimeout();
        onDisconnect?.();

        // Enhanced reconnection logic with connection analysis. Skip entirely
        // when the consumer asked to disconnect (an intentional close must stay
        // closed and not schedule a reconnect).
        if (!intentionalClose.current && reconnect && reconnectAttempts.current < maxReconnectAttempts) {
          // Analyze close code to determine if we should retry
          const shouldRetry = [1000, 1001, 1006, 1011, 1012, 1013, 1014].includes(event.code);

          if (shouldRetry) {
            const backoffDelay = Math.min(
              reconnectInterval * Math.pow(2, reconnectAttempts.current),
              maxReconnectInterval
            );

            reconnectAttempts.current++;
            console.log(`Attempting to reconnect in ${backoffDelay}ms (attempt ${reconnectAttempts.current}/${maxReconnectAttempts})`);

            reconnectTimeoutId.current = setTimeout(() => {
              connect();
            }, backoffDelay);
          } else {
            console.error(`WebSocket closed with non-retryable code: ${event.code}`);
            setConnectionStatus('error');
          }
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          console.error('Max reconnection attempts reached');
          setConnectionStatus('error');
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error occurred:', error);
        setConnectionStatus('error');

        // Enhanced error handling - convert to ErrorEvent for compatibility
        const errorEvent = new ErrorEvent('error', { error });
        onError?.(errorEvent);
      };

      // Set connection timeout
      const connectionTimeout = setTimeout(() => {
        if (ws.current && ws.current.readyState === WebSocket.CONNECTING) {
          console.error('WebSocket connection timeout');
          ws.current.close();
          setConnectionStatus('error');
        }
      }, 10000); // 10 second timeout

      // Clear timeout on successful connection
      const originalOnOpen = ws.current.onopen;
      ws.current.onopen = (event) => {
        clearTimeout(connectionTimeout);
        if (originalOnOpen && ws.current) {
          originalOnOpen.call(ws.current, event);
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
      // Convert error to ErrorEvent for consistency
      const errorEvent = new ErrorEvent('error', { error });
      onError?.(errorEvent);
    }
  }, [url, reconnect, maxReconnectAttempts, reconnectInterval, maxReconnectInterval, onConnect, onMessage, onDisconnect, onError, clearReconnectTimeout, startHeartbeat, processMessageQueue]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      messageQueue.current.push(message);
    }
  }, []);

  const reconnectManually = useCallback(() => {
    disconnect();
    reconnectAttempts.current = 0;
    setTimeout(connect, 100);
  }, [connect]);

  const disconnect = useCallback(() => {
    intentionalClose.current = true;
    clearReconnectTimeout();
    clearHeartbeatTimeout();

    if (ws.current) {
      ws.current.close(1000, 'Manual disconnect');
      ws.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, [clearReconnectTimeout, clearHeartbeatTimeout]);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    connectionStatus,
    lastMessage,
    sendMessage,
    reconnect: reconnectManually,
    disconnect,
    latency
  };
};
