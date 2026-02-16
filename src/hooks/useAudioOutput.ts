import { useRef, useCallback } from 'react';

const SOURCE_SAMPLE_RATE = 24000;

function base64ToInt16(base64: string): Int16Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Int16Array(bytes.buffer);
}

/**
 * AudioBufferSourceNode スケジューリング方式の音声再生。
 *
 * 各チャンクを AudioBufferSourceNode として正確な再生時刻にスケジュールし、
 * Web Audio API に連続再生とリサンプリング（16kHz→ネイティブ）を任せる。
 * リングバッファ方式と異なり、ネットワークジッターに強い。
 */
export function useAudioOutput() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef(0);
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);

  const init = useCallback(async () => {
    if (audioContextRef.current) return;

    const audioContext = new AudioContext();
    audioContextRef.current = audioContext;

    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }

    nextPlayTimeRef.current = 0;
  }, []);

  const playAudio = useCallback((base64: string) => {
    const ctx = audioContextRef.current;
    if (!ctx) return;

    const int16Data = base64ToInt16(base64);

    // 16kHz の AudioBuffer を生成（再生時に AudioContext が自動リサンプリング）
    const audioBuffer = ctx.createBuffer(1, int16Data.length, SOURCE_SAMPLE_RATE);
    const channelData = audioBuffer.getChannelData(0);
    for (let i = 0; i < int16Data.length; i++) {
      channelData[i] = int16Data[i] / 32768;
    }

    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(ctx.destination);

    // 前のチャンクの直後、または今すぐのどちらか遅い方からスケジュール
    const now = ctx.currentTime;
    const startTime = Math.max(nextPlayTimeRef.current, now);
    source.start(startTime);
    nextPlayTimeRef.current = startTime + audioBuffer.duration;

    activeSourcesRef.current.push(source);
    source.onended = () => {
      activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source);
    };
  }, []);

  const clearBuffer = useCallback(() => {
    for (const source of activeSourcesRef.current) {
      try { source.stop(); } catch { /* already stopped */ }
    }
    activeSourcesRef.current = [];
    nextPlayTimeRef.current = 0;
  }, []);

  const cleanup = useCallback(() => {
    clearBuffer();
    audioContextRef.current?.close();
    audioContextRef.current = null;
  }, [clearBuffer]);

  return { init, playAudio, clearBuffer, cleanup };
}
