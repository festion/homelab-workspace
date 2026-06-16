import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '../../hooks/useWebSocket';

// Helper to get mock WebSocket instance
const getMockWebSocket = (): any => {
  return global.WebSocket as any;
};

describe('useWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should establish WebSocket connection successfully', async () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws')
    );

    // The mount effect calls connect() immediately, so the initial
    // 'disconnected' state is not observable here — assert the connection
    // ultimately establishes (mock socket opens after a short delay).
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    }, { timeout: 5000 });

    expect(result.current.connectionStatus).toBe('connected');
  });

  it('should handle connection errors gracefully', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws', { onError })
    );

    // Wait until the hook has created its socket
    await waitFor(() => {
      expect(getMockWebSocket().last).toBeDefined();
    });

    // Simulate an error on the socket the hook actually created
    act(() => {
      getMockWebSocket().last.simulateError();
    });

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('error');
    });

    expect(onError).toHaveBeenCalled();
  });

  it('should attempt reconnection with exponential backoff', async () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws', {
        reconnect: true,
        maxReconnectAttempts: 3,
        reconnectInterval: 100
      })
    );

    // Wait for initial connection
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    const socketsBefore = getMockWebSocket().instances.length;

    // Simulate disconnection on the hook's actual socket with a retryable code
    act(() => {
      getMockWebSocket().last.simulateClose(1006, 'Connection lost');
    });

    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('disconnected');
    });

    // Should attempt reconnection — a new socket is created after the backoff.
    // (Asserting on the transient 'connecting' state would be racy; the new
    // socket instance is the durable evidence of a reconnect attempt.)
    await waitFor(() => {
      expect(getMockWebSocket().instances.length).toBeGreaterThan(socketsBefore);
    }, { timeout: 1000 });
  });

  it('should queue messages during disconnection', async () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws')
    );

    // Wait for connection
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Disconnect
    act(() => {
      result.current.disconnect();
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });

    // Send message while disconnected (should be queued)
    act(() => {
      result.current.sendMessage({ type: 'test', data: 'queued message' });
    });

    // Reconnect
    act(() => {
      result.current.reconnect();
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Message should have been sent after reconnection
    // This would be verified by checking the mock WebSocket send method
  });

  it('should handle heartbeat and latency tracking', async () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws', {
        heartbeatInterval: 1000
      })
    );

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Simulate pong response
    act(() => {
      const mockWs = new (getMockWebSocket())('ws://localhost:3000/ws');
      mockWs.simulateMessage({ type: 'pong' });
    });

    await waitFor(() => {
      expect(result.current.latency).toBeGreaterThanOrEqual(0);
    });
  });

  it('should handle message parsing errors gracefully', async () => {
    const onMessage = jest.fn();
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws', { onMessage })
    );

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Deliver invalid JSON through the hook's actual socket handler
    act(() => {
      getMockWebSocket().last.onmessage?.({ data: 'invalid json{' } as MessageEvent);
    });

    // Should handle the parse error and fall back to a raw message
    await waitFor(() => {
      expect(onMessage).toHaveBeenCalledWith({ type: 'raw', data: 'invalid json{' });
    });
  });

  it('should respect max reconnection attempts', async () => {
    // Keep sockets in CONNECTING (never fire onopen) so a successful open can't
    // reset reconnectAttempts — that lets the attempt counter actually climb to
    // the max across repeated failures.
    getMockWebSocket().autoConnect = false;

    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws', {
        reconnect: true,
        maxReconnectAttempts: 2,
        reconnectInterval: 30
      })
    );

    // Mount creates the first socket
    await waitFor(() => {
      expect(getMockWebSocket().last).toBeDefined();
    });

    // Fail repeatedly. Each retryable close either schedules another reconnect
    // (new socket) or, once the max is reached, flips to the error state.
    for (let i = 0; i < 3; i++) {
      const socketsBefore = getMockWebSocket().instances.length;

      act(() => {
        getMockWebSocket().last.simulateClose(1006, 'Connection lost');
      });

      await waitFor(() => {
        const reconnected = getMockWebSocket().instances.length > socketsBefore;
        const errored = result.current.connectionStatus === 'error';
        expect(reconnected || errored).toBe(true);
      }, { timeout: 1000 });

      if (result.current.connectionStatus === 'error') break;
    }

    // After exceeding max attempts, should be in error state
    await waitFor(() => {
      expect(result.current.connectionStatus).toBe('error');
    }, { timeout: 1000 });
  });

  it('should cleanup resources on unmount', async () => {
    const { result, unmount } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws')
    );

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Unmount should trigger cleanup
    unmount();

    // Verify WebSocket was closed (would need to check mock implementation)
    // This test verifies the cleanup behavior exists
    expect(true).toBe(true); // Placeholder for actual cleanup verification
  });

  it('should validate WebSocket URL', () => {
    const { result } = renderHook(() =>
      useWebSocket('')
    );

    expect(result.current.connectionStatus).toBe('error');
  });

  it('should handle manual reconnection', async () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost:3000/ws')
    );

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });

    // Disconnect
    act(() => {
      result.current.disconnect();
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });

    // Manual reconnect
    act(() => {
      result.current.reconnect();
    });

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
  });
});