/**
 * AudioWorklet: マイク入力 → Int16 PCM 変換
 *
 * AudioContext({ sampleRate: 16000 }) で動作し、
 * Float32 → Int16 に変換して main thread に転送する。
 */
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0] || input[0].length === 0) {
      return true;
    }

    const float32Data = input[0]; // mono channel
    const int16Data = new Int16Array(float32Data.length);

    for (let i = 0; i < float32Data.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Data[i]));
      int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage(int16Data.buffer, [int16Data.buffer]);
    return true;
  }
}

registerProcessor('pcm-capture-processor', PcmCaptureProcessor);
