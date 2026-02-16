"""ツール使用テスト: get_current_time / simple_calculator が音声対話中に呼ばれるか確認。

macOS say で生成した音声をエージェントに送信し、ツール呼び出しの有無を検証する。

使い方:
    # 音声ファイルを事前に生成
    say -v Kyoko -o /tmp/test_time.aiff "今何時ですか？"
    ffmpeg -y -i /tmp/test_time.aiff -f s16le -acodec pcm_s16le -ar 16000 -ac 1 /tmp/test_time.pcm

    say -v Kyoko -o /tmp/test_calc.aiff "3かける5は何ですか？"
    ffmpeg -y -i /tmp/test_calc.aiff -f s16le -acodec pcm_s16le -ar 16000 -ac 1 /tmp/test_calc.pcm

    # テスト実行
    python test_tools.py --test time    # 時刻ツールテスト
    python test_tools.py --test calc    # 計算ツールテスト
    python test_tools.py --test both    # 両方テスト
"""

import argparse
import asyncio
import base64
import os
import sys
import time

import boto3
from strands import tool
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


@tool
def get_current_time() -> str:
    """現在の日本時間を取得します。

    Returns:
        現在の日本時間の文字列
    """
    from datetime import datetime, timedelta, timezone

    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
    weekday = weekday_ja[now.weekday()]
    result = f"{now.year}年{now.month}月{now.day}日({weekday}) {now.strftime('%H:%M')} JST"
    print(f"  🔧 [ツール呼び出し] get_current_time → {result}")
    return result


@tool
def simple_calculator(expression: str) -> str:
    """簡単な計算を行います。四則演算に対応しています。

    Args:
        expression: 計算式（例: "2 + 3", "10 * 5"）

    Returns:
        計算結果の文字列
    """
    allowed_chars = set("0123456789+-*/.() ")
    if not all(c in allowed_chars for c in expression):
        return "エラー: 許可されていない文字が含まれています"
    try:
        result = eval(expression)  # noqa: S307
        print(f"  🔧 [ツール呼び出し] simple_calculator({expression}) → {result}")
        return f"{expression} = {result}"
    except Exception as e:
        return f"計算エラー: {e}"


class FileAudioInput:
    """PCM ファイルから音声を読み込んで送信する。送信後は無音を継続。"""

    def __init__(self, pcm_path: str) -> None:
        with open(pcm_path, "rb") as f:
            raw = f.read()
        self._chunks = [raw[i : i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
        silence_chunk = b"\x00" * CHUNK_SIZE
        self._chunks.extend([silence_chunk] * (3000 // CHUNK_MS))
        self._index = 0
        duration = len(raw) / (SAMPLE_RATE * 2) * 1000
        print(f"  音声: {duration:.0f}ms ({len(raw)} bytes) + 無音 3000ms")

    async def __call__(self) -> BidiAudioInputEvent:
        if self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            self._index += 1
            await asyncio.sleep(CHUNK_MS / 1000)
            audio_b64 = base64.b64encode(chunk).decode("ascii")
            return BidiAudioInputEvent(audio=audio_b64, format="pcm", sample_rate=SAMPLE_RATE, channels=CHANNELS)

        silence = b"\x00" * CHUNK_SIZE
        await asyncio.sleep(CHUNK_MS / 1000)
        audio_b64 = base64.b64encode(silence).decode("ascii")
        return BidiAudioInputEvent(audio=audio_b64, format="pcm", sample_rate=SAMPLE_RATE, channels=CHANNELS)

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass


class ToolTestOutput:
    """ツール呼び出しに注目した出力ハンドラ。"""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.transcript_parts: list[str] = []
        self.audio_bytes_total = 0
        self._first_response_time: float | None = None
        self._start_time: float | None = None

    def set_start_time(self, t: float) -> None:
        self._start_time = t

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
            self.audio_bytes_total += len(audio) if audio else 0
            if self._first_response_time is None and self._start_time:
                self._first_response_time = time.monotonic()
                latency = (self._first_response_time - self._start_time) * 1000
                print(f"  ⏱️ [レイテンシ] 最初の音声レスポンスまで: {latency:.0f}ms")
        else:
            if "ResponseStart" in event_type:
                print(f"  [{event_type}]")
            elif "ResponseComplete" in event_type:
                print(f"  [{event_type}]")
            elif "Usage" in event_type:
                total = getattr(event, "totalTokens", "?")
                print(f"  [トークン] total={total}")
            elif "ToolUse" in event_type or "Tool" in event_type:
                print(f"  🔧 [{event_type}] {event}")
            elif "Error" in event_type:
                print(f"  ❌ [{event_type}] {event}")
            else:
                print(f"  [{event_type}] {event}")

        self.events.append(event_type)

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass


async def run_tool_test(test_type: str, profile: str, region: str) -> dict:
    """ツール使用テストを実行する。"""
    test_configs = {
        "time": {
            "pcm_path": "/tmp/test_time.pcm",
            "description": "時刻ツール（get_current_time）",
            "expected_tool": "get_current_time",
        },
        "calc": {
            "pcm_path": "/tmp/test_calc.pcm",
            "description": "計算ツール（simple_calculator）",
            "expected_tool": "simple_calculator",
        },
    }

    config = test_configs[test_type]
    pcm_path = config["pcm_path"]

    if not os.path.exists(pcm_path):
        print(f"❌ 音声ファイルが見つかりません: {pcm_path}")
        print(f"   先に音声ファイルを生成してください（スクリプト冒頭の使い方を参照）")
        return {"success": False, "error": "missing_audio"}

    print(f"\n{'='*60}")
    print(f"テスト: {config['description']}")
    print(f"{'='*60}")

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
        tools=[stop_conversation, get_current_time, simple_calculator],
        system_prompt=(
            "あなたは日本語の音声アシスタントです。簡潔に日本語で応答してください。"
            "ツールが利用可能な場合は積極的に使ってください。"
            "時刻を聞かれたら get_current_time を使い、計算を頼まれたら simple_calculator を使ってください。"
        ),
    )

    audio_input = FileAudioInput(pcm_path)
    test_output = ToolTestOutput()

    send_complete_time = time.monotonic()
    test_output.set_start_time(send_complete_time)

    try:
        await asyncio.wait_for(
            agent.run(inputs=[audio_input], outputs=[test_output]),
            timeout=30,
        )
    except asyncio.TimeoutError:
        print("\n  --- 30秒タイムアウト ---")

    print(f"\n--- 結果 ---")
    print(f"  受信イベント: {len(test_output.events)}")
    print(f"  イベント種類: {set(test_output.events)}")
    print(f"  音声出力: {test_output.audio_bytes_total} bytes")

    if test_output.transcript_parts:
        print(f"  応答テキスト:")
        for part in test_output.transcript_parts:
            print(f"    → {part}")

    return {
        "success": True,
        "events": test_output.events,
        "transcript": test_output.transcript_parts,
        "audio_bytes": test_output.audio_bytes_total,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="ツール使用テスト")
    parser.add_argument(
        "--test",
        choices=["time", "calc", "both"],
        default="both",
        help="テスト種類 (default: both)",
    )
    parser.add_argument("--profile", default="sandbox", help="AWS プロファイル")
    parser.add_argument("--region", default="us-east-1", help="AWS リージョン")
    args = parser.parse_args()

    tests = ["time", "calc"] if args.test == "both" else [args.test]
    results = {}

    for test_type in tests:
        results[test_type] = await run_tool_test(test_type, args.profile, args.region)

    print(f"\n{'='*60}")
    print("テストサマリー")
    print(f"{'='*60}")
    for test_type, result in results.items():
        status = "✅" if result.get("success") else "❌"
        transcript = " / ".join(result.get("transcript", []))
        print(f"  {status} {test_type}: {transcript or '(応答なし)'}")


if __name__ == "__main__":
    asyncio.run(main())
