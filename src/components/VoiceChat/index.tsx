import { useState, useCallback, useEffect } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket.ts';
import { useAudioInput } from '../../hooks/useAudioInput.ts';
import { useAudioOutput } from '../../hooks/useAudioOutput.ts';
import { ConnectionStatus } from './ConnectionStatus.tsx';
import { MicButton } from './MicButton.tsx';
import { TranscriptView } from './TranscriptView.tsx';
import type { TranscriptEntry } from './types.ts';

export function VoiceChat() {
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const audioOutput = useAudioOutput();

  const handleTranscript = useCallback((role: string, text: string, isFinal: boolean) => {
    setTranscripts((prev) => {
      const lastIdx = prev.length - 1;
      // 同じロールの非finalエントリがあれば上書き（非final→非final も final→確定 も）
      if (lastIdx >= 0 && prev[lastIdx].role === role && !prev[lastIdx].isFinal) {
        const updated = [...prev];
        updated[lastIdx] = { ...updated[lastIdx], text, isFinal };
        return updated;
      }
      return [...prev, { role: role as 'user' | 'assistant', text, isFinal, timestamp: Date.now() }];
    });
    setActiveTool(null);
  }, []);

  const handleInterruption = useCallback(() => {
    audioOutput.clearBuffer();
    setActiveTool(null);
  }, [audioOutput]);

  const handleToolUse = useCallback((name: string) => {
    setActiveTool(name);
  }, []);

  const handleError = useCallback((message: string) => {
    setError(message);
    setTimeout(() => setError(null), 5000);
  }, []);

  const ws = useWebSocket({
    onAudio: audioOutput.playAudio,
    onTranscript: handleTranscript,
    onInterruption: handleInterruption,
    onToolUse: handleToolUse,
    onError: handleError,
  });

  const audioInput = useAudioInput({
    onAudioChunk: useCallback(
      (base64: string) => ws.send({ type: 'audio', audio: base64 }),
      [ws],
    ),
  });

  // 接続時に AudioOutput を初期化
  useEffect(() => {
    if (ws.connectionStatus === 'connected') {
      audioOutput.init();
    }
  }, [ws.connectionStatus, audioOutput]);

  // 切断時にマイクを停止
  useEffect(() => {
    if (ws.connectionStatus === 'disconnected' && audioInput.isRecording) {
      audioInput.stopRecording();
    }
  }, [ws.connectionStatus, audioInput]);

  const handleMicToggle = useCallback(() => {
    if (audioInput.isRecording) {
      audioInput.stopRecording();
    } else {
      audioInput.startRecording();
    }
  }, [audioInput]);

  const handleConnect = useCallback(() => {
    if (ws.connectionStatus === 'disconnected') {
      setTranscripts([]);
      setActiveTool(null);
      setError(null);
      ws.connect();
    } else {
      audioInput.stopRecording();
      audioOutput.cleanup();
      ws.disconnect();
    }
  }, [ws, audioInput, audioOutput]);

  const isConnected = ws.connectionStatus === 'connected';

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      {/* ステータスバー */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-white">
        <ConnectionStatus status={ws.connectionStatus} />
        <button
          onClick={handleConnect}
          className={`
            px-4 py-1.5 rounded-lg text-sm font-medium transition-colors
            ${ws.connectionStatus === 'disconnected'
              ? 'bg-indigo-600 text-white hover:bg-indigo-700'
              : ws.connectionStatus === 'connecting'
                ? 'bg-gray-300 text-gray-500 cursor-wait'
                : 'bg-red-100 text-red-700 hover:bg-red-200'
            }
          `}
          disabled={ws.connectionStatus === 'connecting'}
        >
          {ws.connectionStatus === 'disconnected' ? '接続' : ws.connectionStatus === 'connecting' ? '接続中...' : '切断'}
        </button>
      </div>

      {/* エラー表示 */}
      {error && (
        <div className="mx-4 mt-2 px-4 py-2 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {/* トランスクリプト */}
      <TranscriptView entries={transcripts} activeTool={activeTool} />

      {/* マイクボタン */}
      <div className="flex justify-center py-6 bg-white border-t">
        <MicButton
          isRecording={audioInput.isRecording}
          isConnected={isConnected}
          onToggle={handleMicToggle}
        />
      </div>
    </div>
  );
}
