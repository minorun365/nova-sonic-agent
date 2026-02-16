import { useRef, useCallback } from 'react';

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

export function useAudioOutput() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);

  const init = useCallback(async () => {
    if (audioContextRef.current) return;

    const audioContext = new AudioContext({ sampleRate: 16000 });
    audioContextRef.current = audioContext;

    const workletUrl = new URL('../audio/pcm-playback-processor.js', import.meta.url);
    await audioContext.audioWorklet.addModule(workletUrl);

    const workletNode = new AudioWorkletNode(audioContext, 'pcm-playback-processor');
    workletNodeRef.current = workletNode;

    workletNode.connect(audioContext.destination);
  }, []);

  const playAudio = useCallback((base64: string) => {
    if (!workletNodeRef.current) return;
    const buffer = base64ToArrayBuffer(base64);
    workletNodeRef.current.port.postMessage(buffer, [buffer]);
  }, []);

  const clearBuffer = useCallback(() => {
    workletNodeRef.current?.port.postMessage('clearBuffer');
  }, []);

  const cleanup = useCallback(() => {
    workletNodeRef.current?.disconnect();
    audioContextRef.current?.close();
    workletNodeRef.current = null;
    audioContextRef.current = null;
  }, []);

  return { init, playAudio, clearBuffer, cleanup };
}
