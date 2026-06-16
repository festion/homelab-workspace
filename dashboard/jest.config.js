export default {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  // jsdom URL provides window.location (host/hostname/port/protocol) — jest 30
  // makes window.location non-redefinable, so this replaces the old manual mock.
  testEnvironmentOptions: {
    url: 'http://localhost:3000',
  },
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  transform: {
    // Use the app tsconfig so ts-jest picks up jsx: 'react-jsx' (the root
    // tsconfig.json is references-only and carries no compilerOptions, which
    // left JSX untransformed). isolatedModules speeds up transpile-only.
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: 'tsconfig.app.json',
      isolatedModules: true,
    }],
  },
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.(ts|tsx)',
    '<rootDir>/src/**/?(*.)(test|spec).(ts|tsx)',
  ],
  collectCoverageFrom: [
    'src/**/*.(ts|tsx)',
    '!src/**/*.d.ts',
    '!src/main.tsx',
    '!src/vite-env.d.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
  testTimeout: 10000,
};
