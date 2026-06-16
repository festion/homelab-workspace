import '@testing-library/jest-dom';

// Mock WebSocket for testing
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(_data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock successful send
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      const closeEvent = new CloseEvent('close', { code: code || 1000, reason: reason || '' });
      this.onclose(closeEvent);
    }
  }

  // Helper methods for testing
  simulateMessage(data: any) {
    if (this.onmessage) {
      const messageEvent = new MessageEvent('message', { data: JSON.stringify(data) });
      this.onmessage(messageEvent);
    }
  }

  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      const closeEvent = new CloseEvent('close', { code, reason });
      this.onclose(closeEvent);
    }
  }
}

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any;

// Mock fetch for API testing
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({
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
          name: 'test-repo',
          status: 'clean',
          clone_url: 'https://github.com/test/repo',
          local_path: '/repos/test-repo'
        }
      ]
    }),
  } as Response)
);

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock as any;

// window.location (host/hostname/port/protocol) is provided by jest.config.js
// testEnvironmentOptions.url ('http://localhost:3000'); jest 30 / jsdom no longer
// allows redefining window.location via Object.defineProperty.

// Suppress console warnings in tests unless debugging
const originalWarn = console.warn;
console.warn = jest.fn((message: any) => {
  if (process.env.DEBUG_TESTS) {
    originalWarn(message);
  }
});

// Reset mocks between tests
beforeEach(() => {
  jest.clearAllMocks();
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  localStorageMock.removeItem.mockClear();
  localStorageMock.clear.mockClear();
});
