import { useRef, useState, useCallback } from 'react';

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

interface UseAudioInputProps {
  onAudioChunk: (base64: string) => void;
}

export function useAudioInput(props: UseAudioInputProps) {
  const [isRecording, setIsRecording] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;

  const startRecording = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    streamRef.current = stream;

    const audioContext = new AudioContext({ sampleRate: 16000 });
    audioContextRef.current = audioContext;

    const workletUrl = new URL('../audio/pcm-capture-processor.js', import.meta.url);
    await audioContext.audioWorklet.addModule(workletUrl);

    const source = audioContext.createMediaStreamSource(stream);
    const workletNode = new AudioWorkletNode(audioContext, 'pcm-capture-processor');
    workletNodeRef.current = workletNode;

    workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
      propsRef.current.onAudioChunk(arrayBufferToBase64(event.data));
    };

    source.connect(workletNode);
    workletNode.connect(audioContext.destination);

    setIsRecording(true);
  }, []);

  const stopRecording = useCallback(() => {
    workletNodeRef.current?.disconnect();
    audioContextRef.current?.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    workletNodeRef.current = null;
    audioContextRef.current = null;
    streamRef.current = null;
    setIsRecording(false);
  }, []);

  return { isRecording, startRecording, stopRecording };
}
