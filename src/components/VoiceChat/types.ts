export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

export interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
  isFinal: boolean;
  timestamp: number;
}
