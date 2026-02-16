"""Nova Sonic への接続テスト。

macOS say で生成した実際の音声ファイルを送信し、レスポンスを確認する。
"""

import asyncio
import base64
import os
import sys

from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel
from strands.experimental.bidi.tools import stop_conversation
from strands.experimental.bidi.types.events import (
    BidiAudioInputEvent,
    BidiAudioStreamEvent,
    BidiOutputEvent,
    BidiTranscriptStreamEvent,
)

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_MS = 20
CHUNK_SIZE = SAMPLE_RATE * 2 * CHUNK_MS // 1000  # 640 bytes per 20ms chunk


class FileAudioInput:
    """PCM ファイルから音声を読み込んで送信する。送信後は無音を継続。"""

    def __init__(self, pcm_path: str) -> None:
        with open(pcm_path, "rb") as f:
            raw = f.read()
        self._chunks = [raw[i : i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
        # 送信後に 3秒の無音を追加（VAD のターン検出用）
        silence_chunk = b"\x00" * CHUNK_SIZE
        self._chunks.extend([silence_chunk] * (3000 // CHUNK_MS))
        self._index = 0
        duration = len(raw) / (SAMPLE_RATE * 2) * 1000
        print(f"[入力] 音声ファイル: {pcm_path}")
        print(f"  - 音声: {duration:.0f}ms ({len(raw)} bytes)")
        print(f"  - 無音: 3000ms")
        print(f"  - 合計チャンク数: {len(self._chunks)}")

    async def __call__(self) -> BidiAudioInputEvent:
        if self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            self._index += 1
            if self._index == 1:
                print("[入力] 音声送信開始...")
            elif self._index == len(self._chunks):
                print("[入力] 全チャンク送信完了。レスポンス待機...")
            await asyncio.sleep(CHUNK_MS / 1000)
            audio_b64 = base64.b64encode(chunk).decode("ascii")
            return BidiAudioInputEvent(audio=audio_b64, format="pcm", sample_rate=SAMPLE_RATE, channels=CHANNELS)

        # 以降は無音を送り続けて接続を維持
        silence = b"\x00" * CHUNK_SIZE
        await asyncio.sleep(CHUNK_MS / 1000)
        audio_b64 = base64.b64encode(silence).decode("ascii")
        return BidiAudioInputEvent(audio=audio_b64, format="pcm", sample_rate=SAMPLE_RATE, channels=CHANNELS)

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass


class TestOutput:
    """受信イベントを表示する。"""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.transcript_parts: list[str] = []
        self.audio_bytes_total = 0
        self._audio_event_count = 0

    async def __call__(self, event: BidiOutputEvent) -> None:
        event_type = type(event).__name__

        if isinstance(event, BidiTranscriptStreamEvent):
            role = getattr(event, "role", "?")
            text = getattr(event, "text", "")
            is_final = getattr(event, "is_final", False)
            marker = "[確定]" if is_final else "[途中]"
            print(f"  {marker} ({role}): {text}")
            if role == "assistant" and is_final and text:
                self.transcript_parts.append(text)
        elif isinstance(event, BidiAudioStreamEvent):
            audio = getattr(event, "audio", "")
            audio_len = len(audio) if audio else 0
            self.audio_bytes_total += audio_len
            self._audio_event_count += 1
            if self._audio_event_count <= 3:
                print(f"  [音声出力] chunk #{self._audio_event_count}: {audio_len} bytes")
            elif self._audio_event_count == 4:
                print(f"  [音声出力] ... (以降省略)")
        else:
            if "Usage" in event_type:
                d = dict(event) if hasattr(event, "items") else {}
                total = d.get("totalTokens", getattr(event, "totalTokens", "?"))
                output = d.get("outputTokens", getattr(event, "outputTokens", "?"))
                print(f"  [トークン] total={total}, output={output}")
            elif "ResponseStart" in event_type or "ResponseComplete" in event_type:
                print(f"  [{event_type}]")
            else:
                print(f"  [{event_type}] {event}")

        self.events.append(event_type)

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass


async def test_connection() -> None:
    region = os.environ.get("AWS_REGION", "us-east-1")
    print(f"Nova Sonic 接続テスト (region: {region})")
    print("=" * 60)

    model = BidiNovaSonicModel(
        model_id="amazon.nova-sonic-v1:0",
        provider_config={
            "audio": {
                "input_sample_rate": SAMPLE_RATE,
                "output_sample_rate": SAMPLE_RATE,
                "voice": "tiffany",
            },
        },
        client_config={
            "region": region,
        },
    )

    agent = BidiAgent(
        model=model,
        tools=[stop_conversation],
        system_prompt="あなたは日本語の音声アシスタントです。簡潔に日本語で応答してください。",
    )

    test_input = FileAudioInput("/tmp/test_speech_ja.pcm")
    test_out = TestOutput()

    print("-" * 60)

    try:
        await asyncio.wait_for(
            agent.run(inputs=[test_input], outputs=[test_out]),
            timeout=30,
        )
    except asyncio.TimeoutError:
        print("\n--- 30秒タイムアウト ---")
    except Exception as e:
        print(f"\nエラー: {type(e).__name__}: {e}", file=sys.stderr)

    print("=" * 60)
    print(f"受信イベント数: {len(test_out.events)}")
    print(f"イベント種類: {set(test_out.events)}")
    print(f"音声出力合計: {test_out.audio_bytes_total} bytes ({test_out._audio_event_count} chunks)")
    if test_out.transcript_parts:
        print(f"\nアシスタントの応答テキスト:")
        for part in test_out.transcript_parts:
            print(f"  {part}")
    else:
        print("\n(テキスト応答は受信されませんでした)")


if __name__ == "__main__":
    asyncio.run(test_connection())
