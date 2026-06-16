import '@testing-library/jest-dom';

// Mock WebSocket for testing
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  // Registry so tests can drive the socket the hook actually created
  // (the hook does `new WebSocket(url)` internally — tests must reach THAT
  // instance, not a throwaway one). MockWebSocket.last is the newest socket.
  static instances: MockWebSocket[] = [];
  // When false, sockets stay CONNECTING (never fire onopen). Lets reconnection
  // tests accumulate attempts without onopen resetting the counter.
  static autoConnect = true;
  static get last(): MockWebSocket {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    if (MockWebSocket.autoConnect) {
      // Simulate connection after a short delay
      setTimeout(() => {
        this.readyState = MockWebSocket.OPEN;
        if (this.onopen) {
          this.onopen(new Event('open'));
        }
      }, 100);
    }
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

// Mock localStorage — jsdom provides a real localStorage that shadows a plain
// `global.localStorage =` assignment, so define it as an own property on window.
// getItem returns null by default (matches the real Storage API for missing
// keys); the default is re-asserted in beforeEach so a per-test mockReturnValue
// can't leak to later tests.
const localStorageMock = {
  getItem: jest.fn(() => null as string | null),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
  configurable: true,
});

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
  // Re-assert the default after clearAllMocks (which clears calls but keeps a
  // leaked per-test mockReturnValue).
  localStorageMock.getItem.mockReturnValue(null);
  // Reset WebSocket registry/behavior so tests don't see prior sockets.
  MockWebSocket.instances = [];
  MockWebSocket.autoConnect = true;
});
