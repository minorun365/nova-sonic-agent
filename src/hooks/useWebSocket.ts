import { useRef, useState, useCallback } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { SignatureV4 } from '@smithy/signature-v4';
import { HttpRequest } from '@smithy/protocol-http';
import { Sha256 } from '@aws-crypto/sha256-js';
import outputs from '../../amplify_outputs.json';
import type { ConnectionStatus } from '../components/VoiceChat/types.ts';

interface UseWebSocketProps {
  onAudio: (base64: string) => void;
  onTranscript: (role: string, text: string, isFinal: boolean) => void;
  onInterruption: () => void;
  onToolUse: (name: string) => void;
  onError: (message: string) => void;
}

/**
 * SigV4 事前署名 WebSocket URL を生成する。
 * Python botocore の create_presigned_url() と同等の処理を行う。
 */
async function createPresignedUrl(runtimeArn: string): Promise<string> {
  const session = await fetchAuthSession();
  const credentials = session.credentials;
  if (!credentials) throw new Error('AWS credentials not available');

  const arnParts = runtimeArn.split(':');
  const region = arnParts[3];

  const hostname = `bedrock-agentcore.${region}.amazonaws.com`;
  // ARN はエンコードしない（公式 Python サンプル準拠）
  const path = `/runtimes/${runtimeArn}/ws`;

  const signer = new SignatureV4({
    service: 'bedrock-agentcore',
    region,
    credentials: {
      accessKeyId: credentials.accessKeyId,
      secretAccessKey: credentials.secretAccessKey,
      sessionToken: credentials.sessionToken,
    },
    sha256: Sha256,
    // デフォルト true: パス内の ":" を "%3A" にエンコードして署名（botocore と一致）
  });

  const request = new HttpRequest({
    method: 'GET',
    protocol: 'https:',
    hostname,
    path,
    query: { qualifier: 'DEFAULT' },
    headers: { host: hostname },
  });

  const presigned = await signer.presign(request, { expiresIn: 300 });

  // RFC 3986 エンコーディングでクエリ文字列を構築
  // （URLSearchParams は form-urlencoded で space→"+" になり SigV4 と不一致の可能性）
  const queryParts = Object.entries(presigned.query ?? {})
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&');

  return `wss://${hostname}${path}?${queryParts}`;
}

export function useWebSocket(props: UseWebSocketProps) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;

  const connect = useCallback(async () => {
    setConnectionStatus('connecting');

    try {
      const runtimeArn = outputs.custom?.agentRuntimeArn;
      if (!runtimeArn) throw new Error('Runtime ARN not found in Amplify config');

      const url = await createPresignedUrl(runtimeArn);
      console.log('[WebSocket] Connecting to:', url.substring(0, 150) + '...');

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnectionStatus('connected');

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string);
          const cb = propsRef.current;
          switch (data.type) {
            case 'audio':
              cb.onAudio(data.audio);
              break;
            case 'transcript':
              cb.onTranscript(data.role, data.text, data.is_final);
              break;
            case 'interruption':
              cb.onInterruption();
              break;
            case 'tool_use':
              cb.onToolUse(data.name);
              break;
            case 'error':
              cb.onError(data.message);
              break;
          }
        } catch {
          console.warn('Failed to parse WebSocket message');
        }
      };

      ws.onerror = () => propsRef.current.onError('WebSocket connection error');
      ws.onclose = () => setConnectionStatus('disconnected');
    } catch (error) {
      setConnectionStatus('disconnected');
      propsRef.current.onError(error instanceof Error ? error.message : 'Connection failed');
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnectionStatus('disconnected');
  }, []);

  const send = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { connectionStatus, connect, disconnect, send };
}
