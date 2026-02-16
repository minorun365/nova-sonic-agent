/**
 * AudioWorklet: Int16 PCM → スピーカー再生
 *
 * リングバッファで低レイテンシ再生を実現。
 * clearBuffer メッセージで割り込み時にバッファをクリアする。
 */
class PcmPlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // リングバッファ（最大 5 秒分 @ 16kHz）
    this.bufferSize = 16000 * 5;
    this.buffer = new Float32Array(this.bufferSize);
    this.writeIndex = 0;
    this.readIndex = 0;
    this.samplesAvailable = 0;

    this.port.onmessage = (event) => {
      if (event.data === 'clearBuffer') {
        this.writeIndex = 0;
        this.readIndex = 0;
        this.samplesAvailable = 0;
        return;
      }

      // Int16 PCM データを Float32 に変換してバッファに追加
      const int16Data = new Int16Array(event.data);
      for (let i = 0; i < int16Data.length; i++) {
        if (this.samplesAvailable >= this.bufferSize) {
          // バッファ満杯時は古いデータを上書き
          this.readIndex = (this.readIndex + 1) % this.bufferSize;
          this.samplesAvailable--;
        }
        this.buffer[this.writeIndex] = int16Data[i] / 32768;
        this.writeIndex = (this.writeIndex + 1) % this.bufferSize;
        this.samplesAvailable++;
      }
    };
  }

  process(inputs, outputs) {
    const output = outputs[0];
    if (!output || !output[0]) return true;

    const channel = output[0];

    for (let i = 0; i < channel.length; i++) {
      if (this.samplesAvailable > 0) {
        channel[i] = this.buffer[this.readIndex];
        this.readIndex = (this.readIndex + 1) % this.bufferSize;
        this.samplesAvailable--;
      } else {
        channel[i] = 0; // 無音
      }
    }

    return true;
  }
}

registerProcessor('pcm-playback-processor', PcmPlaybackProcessor);
