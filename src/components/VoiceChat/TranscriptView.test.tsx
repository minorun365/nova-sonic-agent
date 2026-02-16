import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TranscriptView } from './TranscriptView.tsx';
import type { TranscriptEntry } from './types.ts';

describe('TranscriptView', () => {
  it('エントリがないときプレースホルダーを表示', () => {
    render(<TranscriptView entries={[]} activeTool={null} />);
    expect(screen.getByText('マイクボタンを押して話しかけてください')).toBeInTheDocument();
  });

  it('ユーザーメッセージを表示', () => {
    const entries: TranscriptEntry[] = [
      { role: 'user', text: 'こんにちは', isFinal: true, timestamp: Date.now() },
    ];
    render(<TranscriptView entries={entries} activeTool={null} />);
    expect(screen.getByText('こんにちは')).toBeInTheDocument();
  });

  it('アシスタントメッセージを表示', () => {
    const entries: TranscriptEntry[] = [
      { role: 'assistant', text: 'お手伝いします', isFinal: true, timestamp: Date.now() },
    ];
    render(<TranscriptView entries={entries} activeTool={null} />);
    expect(screen.getByText('お手伝いします')).toBeInTheDocument();
  });

  it('ツール実行中の表示', () => {
    render(<TranscriptView entries={[]} activeTool="get_current_time" />);
    expect(screen.getByText('get_current_time を実行中...')).toBeInTheDocument();
  });

  it('複数エントリの会話表示', () => {
    const entries: TranscriptEntry[] = [
      { role: 'user', text: '今何時？', isFinal: true, timestamp: 1 },
      { role: 'assistant', text: '15時です', isFinal: true, timestamp: 2 },
    ];
    render(<TranscriptView entries={entries} activeTool={null} />);
    expect(screen.getByText('今何時？')).toBeInTheDocument();
    expect(screen.getByText('15時です')).toBeInTheDocument();
  });

  it('非finalエントリはopacity-60クラスを持つ', () => {
    const entries: TranscriptEntry[] = [
      { role: 'user', text: 'まだ途中...', isFinal: false, timestamp: Date.now() },
    ];
    render(<TranscriptView entries={entries} activeTool={null} />);
    const el = screen.getByText('まだ途中...');
    expect(el.className).toContain('opacity-60');
  });
});
