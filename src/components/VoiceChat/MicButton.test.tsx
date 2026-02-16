import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MicButton } from './MicButton.tsx';

describe('MicButton', () => {
  it('接続済みでクリック可能', () => {
    const onToggle = vi.fn();
    render(<MicButton isRecording={false} isConnected={true} onToggle={onToggle} />);

    const button = screen.getByRole('button');
    expect(button).not.toBeDisabled();

    fireEvent.click(button);
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('未接続でクリック不可', () => {
    const onToggle = vi.fn();
    render(<MicButton isRecording={false} isConnected={false} onToggle={onToggle} />);

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('録音中はaria-labelが変わる', () => {
    render(<MicButton isRecording={true} isConnected={true} onToggle={() => {}} />);
    expect(screen.getByLabelText('マイクをオフにする')).toBeInTheDocument();
  });

  it('停止中はaria-labelが変わる', () => {
    render(<MicButton isRecording={false} isConnected={true} onToggle={() => {}} />);
    expect(screen.getByLabelText('マイクをオンにする')).toBeInTheDocument();
  });
});
