import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAudioOutput } from './useAudioOutput.ts';

describe('useAudioOutput', () => {
  it('init で AudioContext を作成', async () => {
    const { result } = renderHook(() => useAudioOutput());

    await act(async () => {
      await result.current.init();
    });

    // 2回目の init は何もしない（冪等）
    await act(async () => {
      await result.current.init();
    });
  });

  it('init 前の playAudio は安全にスキップされる', () => {
    const { result } = renderHook(() => useAudioOutput());

    // workletNode が null なのでエラーにならない
    act(() => {
      result.current.playAudio('AAAA');
    });
  });

  it('init 前の clearBuffer は安全にスキップされる', () => {
    const { result } = renderHook(() => useAudioOutput());

    act(() => {
      result.current.clearBuffer();
    });
  });

  it('cleanup を呼べる', async () => {
    const { result } = renderHook(() => useAudioOutput());

    await act(async () => {
      await result.current.init();
    });

    act(() => {
      result.current.cleanup();
    });
  });
});
