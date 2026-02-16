"""レイテンシ計測テスト。

発話終了から各種レスポンスイベントまでの時間を計測する。
複数回実行して安定性を確認する。

使い方:
    say -v Kyoko -o /tmp/test_simple.aiff "お元気ですか"
    ffmpeg -y -i /tmp/test_simple.aiff -f s16le -acodec pcm_s16le -ar 16000 -ac 1 /tmp/test_simple.pcm

    python test_latency.py                      # 1回実行
    python test_latency.py --runs 3             # 3回実行して平均を取る
    python test_latency.py --pcm /tmp/other.pcm # 別の音声ファイルを使用
"""

import argparse
import asyncio
import base64
import time

import boto3
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
CHUNK_SIZE = SAMPLE_RATE * 2 * CHUNK_MS // 1000


class TimedAudioInput:
    """PCM ファイルを送信し、無音開始タイミングを記録する。"""

    def __init__(self, pcm_path: str) -> None:
        with open(pcm_path, "rb") as f:
            raw = f.read()
        self._chunks = [raw[i : i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
        silence = b"\x00" * CHUNK_SIZE
        self._silence_chunks = [silence] * (3000 // CHUNK_MS)
        self._index = 0
        self._silence_index = 0
        self._in_silence = False
        self.silence_start_time: float | None = None
        duration = len(raw) / (SAMPLE_RATE * 2) * 1000
        print(f"  音声: {duration:.0f}ms + 無音 3000ms")

    async def __call__(self) -> BidiAudioInputEvent:
        if not self._in_silence and self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            self._index += 1
            if self._index == len(self._chunks):
                self._in_silence = True
                self.silence_start_time = time.monotonic()
        elif self._in_silence and self._silence_index < len(self._silence_chunks):
            chunk = self._silence_chunks[self._silence_index]
            self._silence_index += 1
        else:
            chunk = b"\x00" * CHUNK_SIZE

        await asyncio.sleep(CHUNK_MS / 1000)
        audio_b64 = base64.b64encode(chunk).decode("ascii")
        return BidiAudioInputEvent(audio=audio_b64, format="pcm", sample_rate=SAMPLE_RATE, channels=CHANNELS)

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass


class LatencyOutput:
    """各種レスポンスイベントのタイミングを記録する。"""

    def __init__(self, audio_input: TimedAudioInput) -> None:
        self._audio_input = audio_input
        self.first_response_start: float | None = None
        self.first_transcript: float | None = None
        self.first_audio: float | None = None
        self.first_final_transcript: float | None = None
        self.transcript_text = ""
        self._response_started = False

    async def __call__(self, event: BidiOutputEvent) -> None:
        now = time.monotonic()
        event_type = type(event).__name__

        if isinstance(event, BidiTranscriptStreamEvent):
            role = getattr(event, "role", "?")
            text = getattr(event, "text", "")
            is_final = getattr(event, "is_final", False)
            if role == "assistant":
                if self.first_transcript is None:
                    self.first_transcript = now
                if is_final and self.first_final_transcript is None:
                    self.first_final_transcript = now
                    self.transcript_text = text
        elif isinstance(event, BidiAudioStreamEvent):
            if self.first_audio is None:
                self.first_audio = now
        elif "ResponseStart" in event_type:
            if self._response_started and self.first_response_start is None:
                self.first_response_start = now
            self._response_started = True

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass

    def get_latencies(self) -> dict[str, float | None]:
        """発話終了（無音開始）からの各レイテンシをmsで返す。"""
        base = self._audio_input.silence_start_time
        if base is None:
            return {}

        def delta(t: float | None) -> float | None:
            return (t - base) * 1000 if t else None

        return {
            "response_start": delta(self.first_response_start),
            "first_transcript": delta(self.first_transcript),
            "first_audio": delta(self.first_audio),
            "final_transcript": delta(self.first_final_transcript),
        }


async def run_once(pcm_path: str, profile: str, region: str, run_num: int) -> dict:
    """1回のレイテンシ計測を実行する。"""
    print(f"\n--- Run #{run_num} ---")

    session = boto3.Session(profile_name=profile, region_name=region)

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
            "boto_session": session,
        },
    )

    agent = BidiAgent(
        model=model,
        tools=[stop_conversation],
        system_prompt="あなたは日本語の音声アシスタントです。簡潔に日本語で応答してください。",
    )

    audio_input = TimedAudioInput(pcm_path)
    output = LatencyOutput(audio_input)

    try:
        await asyncio.wait_for(
            agent.run(inputs=[audio_input], outputs=[output]),
            timeout=20,
        )
    except asyncio.TimeoutError:
        pass

    latencies = output.get_latencies()
    print(f"  応答テキスト: {output.transcript_text}")
    print(f"  レイテンシ:")
    for key, val in latencies.items():
        if val is not None:
            print(f"    {key}: {val:.0f}ms")
        else:
            print(f"    {key}: N/A")

    return latencies


async def main() -> None:
    parser = argparse.ArgumentParser(description="レイテンシ計測テスト")
    parser.add_argument("--pcm", default="/tmp/test_simple.pcm", help="PCM 音声ファイル")
    parser.add_argument("--runs", type=int, default=3, help="実行回数 (default: 3)")
    parser.add_argument("--profile", default="sandbox", help="AWS プロファイル")
    parser.add_argument("--region", default="us-east-1", help="AWS リージョン")
    args = parser.parse_args()

    print("=" * 60)
    print("レイテンシ計測テスト")
    print("=" * 60)
    print(f"音声ファイル: {args.pcm}")
    print(f"実行回数: {args.runs}")

    all_latencies: list[dict] = []
    for i in range(args.runs):
        result = await run_once(args.pcm, args.profile, args.region, i + 1)
        all_latencies.append(result)

    print(f"\n{'='*60}")
    print("サマリー")
    print(f"{'='*60}")

    metrics = ["response_start", "first_transcript", "first_audio", "final_transcript"]
    labels = {
        "response_start": "ResponseStart（応答処理開始）",
        "first_transcript": "最初のトランスクリプト（途中）",
        "first_audio": "最初の音声出力",
        "final_transcript": "確定トランスクリプト",
    }

    for metric in metrics:
        values = [r.get(metric) for r in all_latencies if r.get(metric) is not None]
        if values:
            avg = sum(values) / len(values)
            min_v = min(values)
            max_v = max(values)
            print(f"  {labels[metric]}:")
            print(f"    平均: {avg:.0f}ms  最小: {min_v:.0f}ms  最大: {max_v:.0f}ms  (n={len(values)})")
        else:
            print(f"  {labels[metric]}: データなし")


if __name__ == "__main__":
    asyncio.run(main())
