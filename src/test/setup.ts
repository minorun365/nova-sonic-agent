import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// テスト間の DOM クリーンアップ
afterEach(() => {
  cleanup();
});

// Element.scrollTo モック（jsdom に未実装）
Element.prototype.scrollTo = function () {};

// AudioContext モック
class MockAudioContext {
  sampleRate = 16000;
  state = 'running';
  destination = {};
  async close() { this.state = 'closed'; }
  createMediaStreamSource() {
    return { connect: () => ({}) };
  }
  audioWorklet = {
    addModule: async () => {},
  };
}

class MockAudioWorkletNode {
  port = {
    onmessage: null as ((event: MessageEvent) => void) | null,
    postMessage: () => {},
  };
  connect() { return this; }
  disconnect() {}
}

Object.defineProperty(globalThis, 'AudioContext', { value: MockAudioContext });
Object.defineProperty(globalThis, 'AudioWorkletNode', { value: MockAudioWorkletNode });

// MediaDevices モック
Object.defineProperty(navigator, 'mediaDevices', {
  value: {
    getUserMedia: async () => ({
      getTracks: () => [{ stop: () => {} }],
    }),
  },
});

// URL.createObjectURL モック
URL.createObjectURL = () => 'blob:mock';
URL.revokeObjectURL = () => {};
