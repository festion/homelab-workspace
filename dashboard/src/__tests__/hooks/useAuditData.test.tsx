import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuditData } from '../../hooks/useAuditData';

// Mock the useConnectionStatus hook
jest.mock('../../hooks/useConnectionStatus', () => ({
  useConnectionStatus: jest.fn(() => ({
    isConnected: true,
    connectionStatus: 'connected',
    latency: 50,
    clientCount: 1,
    uptime: 3600,
    lastUpdate: '2025-01-01T00:00:00Z',
    connectionQuality: 'excellent',
    reconnect: jest.fn(),
    disconnect: jest.fn()
  }))
}));

const mockApiResponse = {
  timestamp: '2025-01-01T00:00:00Z',
  health_status: 'green',
  summary: {
    total: 10,
    clean: 8,
    dirty: 1,
    missing: 1,
    extra: 0
  },
  repos: [
    {
      name: 'test-repo-1',
      status: 'clean',
      clone_url: 'https://github.com/test/repo1',
      local_path: '/repos/test-repo-1'
    },
    {
      name: 'test-repo-2',
      status: 'dirty',
      clone_url: 'https://github.com/test/repo2',
      local_path: '/repos/test-repo-2'
    }
  ]
};

describe('useAuditData', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockApiResponse),
    });
  });

  it('should load audit data via polling by default', async () => {
    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: false })
    );

    // Initially loading
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBe(null);

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockApiResponse);
    expect(result.current.dataSource).toBe('polling');
    expect(result.current.error).toBe(null);
  });

  it('should handle API fetch errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: false })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toContain('Failed to fetch data');
    expect(result.current.data).toBe(null);
  });

  it('should validate audit data structure', async () => {
    const invalidData = {
      timestamp: '2025-01-01T00:00:00Z',
      // missing health_status, summary, repos
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(invalidData),
    });

    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: false })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toContain('Invalid data received from API');
    expect(result.current.data).toBe(null);
  });

  it('should toggle between real-time and polling modes', async () => {
    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: true })
    );

    // Initially should attempt WebSocket (real-time)
    expect(result.current.isRealTime).toBe(true);

    // Disable real-time
    act(() => {
      result.current.disableRealTime();
    });

    expect(result.current.isRealTime).toBe(false);

    // Enable real-time
    act(() => {
      result.current.enableRealTime();
    });

    expect(result.current.isRealTime).toBe(true);

    // Toggle
    act(() => {
      result.current.toggleRealTime();
    });

    expect(result.current.isRealTime).toBe(false);
  });

  it('should persist real-time preference in localStorage', async () => {
    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: true })
    );

    // Enable real-time
    act(() => {
      result.current.enableRealTime();
    });

    expect(localStorage.setItem).toHaveBeenCalledWith('auditData.realTime', 'true');

    // Disable real-time
    act(() => {
      result.current.disableRealTime();
    });

    expect(localStorage.setItem).toHaveBeenCalledWith('auditData.realTime', 'false');
  });

  it('should load real-time preference from localStorage', () => {
    (localStorage.getItem as jest.Mock).mockReturnValue('false');

    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: true })
    );

    expect(result.current.isRealTime).toBe(false);
  });

  it('should refresh data manually', async () => {
    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: false })
    );

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Manual refresh
    act(() => {
      result.current.refreshData();
    });

    // Should trigger another fetch
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it('should detect data changes and avoid unnecessary updates', async () => {
    const { result } = renderHook(() =>
      useAuditData({ 
        enableWebSocket: false,
        pollingInterval: 100 // Fast polling for test
      })
    );

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const initialData = result.current.data;

    // Mock same data response
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockApiResponse),
    });

    // Wait for polling cycle
    await new Promise(resolve => setTimeout(resolve, 150));

    // Data should remain the same object (no unnecessary re-render)
    expect(result.current.data).toBe(initialData);
  });

  it('should handle WebSocket message updates', async () => {
    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: true })
    );

    // Wait for initial setup
    await waitFor(() => {
      expect(result.current.isRealTime).toBe(true);
    });

    // useConnectionStatus is mocked as connected (isConnected: true), so with
    // real-time enabled the hook selects the WebSocket data source.
    await waitFor(() => {
      expect(result.current.dataSource).toBe('websocket');
    });
  });

  it('should handle different polling intervals', async () => {
    const { result, rerender } = renderHook(
      ({ pollingInterval }) => useAuditData({ enableWebSocket: false, pollingInterval }),
      { initialProps: { pollingInterval: 5000 } }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Change polling interval
    rerender({ pollingInterval: 10000 });

    // Should handle the change without errors
    expect(result.current.data).toEqual(mockApiResponse);
  });

  it('should cleanup polling on unmount', async () => {
    const { unmount } = renderHook(() =>
      useAuditData({ enableWebSocket: false, pollingInterval: 100 })
    );

    // Unmount should cleanup intervals
    unmount();

    // Wait to ensure no more polling happens
    await new Promise(resolve => setTimeout(resolve, 200));

    // If polling was properly cleaned up, fetch count should remain stable
    const fetchCallCount = (global.fetch as jest.Mock).mock.calls.length;
    
    await new Promise(resolve => setTimeout(resolve, 200));
    
    expect((global.fetch as jest.Mock).mock.calls.length).toBe(fetchCallCount);
  });

  it('should handle HTTP error responses', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ error: 'Server error' }),
    });

    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: false })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toContain('HTTP error! status: 500');
    expect(result.current.data).toBe(null);
  });

  it('should validate summary data types', async () => {
    const invalidSummaryData = {
      ...mockApiResponse,
      summary: {
        total: '10', // Should be number
        clean: 8,
        dirty: 1,
        missing: 1,
        extra: 0
      }
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(invalidSummaryData),
    });

    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: false })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toContain('Invalid data received from API');
  });

  it('should filter invalid repos from response', async () => {
    const dataWithInvalidRepos = {
      ...mockApiResponse,
      repos: [
        ...mockApiResponse.repos,
        { name: 'valid-repo', status: 'clean' },
        { invalidRepo: true }, // Missing required fields
        null, // Invalid repo
        { name: 123, status: 'clean' } // Invalid name type
      ]
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(dataWithInvalidRepos),
    });

    const { result } = renderHook(() =>
      useAuditData({ enableWebSocket: false })
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Should have filtered out invalid repos
    expect(result.current.data?.repos).toHaveLength(3); // 2 original + 1 valid
    expect(result.current.error).toBe(null);
  });
});