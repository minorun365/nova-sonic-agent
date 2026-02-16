import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAudioInput } from './useAudioInput.ts';

describe('useAudioInput', () => {
  it('初期状態は録音していない', () => {
    const onAudioChunk = vi.fn();
    const { result } = renderHook(() => useAudioInput({ onAudioChunk }));

    expect(result.current.isRecording).toBe(false);
  });

  it('startRecording で isRecording が true になる', async () => {
    const onAudioChunk = vi.fn();
    const { result } = renderHook(() => useAudioInput({ onAudioChunk }));

    await act(async () => {
      await result.current.startRecording();
    });

    expect(result.current.isRecording).toBe(true);
  });

  it('stopRecording で isRecording が false に戻る', async () => {
    const onAudioChunk = vi.fn();
    const { result } = renderHook(() => useAudioInput({ onAudioChunk }));

    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.isRecording).toBe(true);

    act(() => {
      result.current.stopRecording();
    });
    expect(result.current.isRecording).toBe(false);
  });
});
