import { vi } from 'vitest';

/** Amplify モジュールのモック */
export function mockAmplify() {
  vi.mock('aws-amplify', () => ({
    Amplify: {
      configure: vi.fn(),
      getConfig: vi.fn(() => ({
        custom: {
          agentRuntimeArn: 'arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/test-runtime',
          environment: 'sandbox',
        },
      })),
    },
  }));

  vi.mock('aws-amplify/auth', () => ({
    fetchAuthSession: vi.fn(async () => ({
      tokens: {
        accessToken: { toString: () => 'mock-access-token' },
      },
    })),
  }));

  vi.mock('aws-amplify/utils', () => ({
    I18n: { putVocabularies: vi.fn(), setLanguage: vi.fn() },
  }));

  vi.mock('@aws-amplify/ui-react', () => ({
    Authenticator: ({ children }: { children: (props: { signOut: () => void }) => React.ReactNode }) =>
      children({ signOut: vi.fn() }),
    translations: {},
  }));
}
