import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConnectionStatus } from './ConnectionStatus.tsx';

describe('ConnectionStatus', () => {
  it('未接続状態を表示', () => {
    render(<ConnectionStatus status="disconnected" />);
    expect(screen.getByText('未接続')).toBeInTheDocument();
  });

  it('接続中状態を表示', () => {
    render(<ConnectionStatus status="connecting" />);
    expect(screen.getByText('接続中...')).toBeInTheDocument();
  });

  it('接続済み状態を表示', () => {
    render(<ConnectionStatus status="connected" />);
    expect(screen.getByText('接続済み')).toBeInTheDocument();
  });
});
