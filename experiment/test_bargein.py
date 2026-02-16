"""割り込み（barge-in）テスト。

エージェントが長い応答を生成中に、途中で新しい音声を送信し、
BidiInterruptionEvent が発生するか確認する。

使い方:
    # 音声ファイルを事前に生成
    say -v Kyoko -o /tmp/test_long.aiff "日本の都道府県を北から順に全部教えてください"
    ffmpeg -y -i /tmp/test_long.aiff -f s16le -acodec pcm_s16le -ar 16000 -ac 1 /tmp/test_long.pcm

    say -v Kyoko -o /tmp/test_interrupt.aiff "ストップ、やめてください"
    ffmpeg -y -i /tmp/test_interrupt.aiff -f s16le -acodec pcm_s16le -ar 16000 -ac 1 /tmp/test_interrupt.pcm

    python test_bargein.py
"""

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


class BargeInAudioInput:
    """最初の質問を送り、応答が始まったら割り込み音声を送信する。"""

    def __init__(self, question_pcm: str, interrupt_pcm: str, output_handler: "BargeInOutput") -> None:
        # 質問音声を読み込み
        with open(question_pcm, "rb") as f:
            raw = f.read()
        self._question_chunks = [raw[i : i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
        q_duration = len(raw) / (SAMPLE_RATE * 2) * 1000
        print(f"  質問音声: {q_duration:.0f}ms ({len(raw)} bytes)")

        # 質問後の無音（VAD トリガー）
        silence = b"\x00" * CHUNK_SIZE
        self._silence_chunks = [silence] * (3000 // CHUNK_MS)

        # 割り込み音声を読み込み
        with open(interrupt_pcm, "rb") as f:
            raw2 = f.read()
        self._interrupt_chunks = [raw2[i : i + CHUNK_SIZE] for i in range(0, len(raw2), CHUNK_SIZE)]
        i_duration = len(raw2) / (SAMPLE_RATE * 2) * 1000
        print(f"  割り込み音声: {i_duration:.0f}ms ({len(raw2)} bytes)")

        # 割り込み後の無音
        self._interrupt_silence = [silence] * (3000 // CHUNK_MS)

        self._output = output_handler
        self._phase = "question"  # question → silence → wait → interrupt → interrupt_silence → done
        self._index = 0
        self._interrupt_sent = False

    async def __call__(self) -> BidiAudioInputEvent:
        chunk = None

        if self._phase == "question":
            if self._index < len(self._question_chunks):
                chunk = self._question_chunks[self._index]
                self._index += 1
            else:
                self._phase = "silence"
                self._index = 0
                print("  [入力] 質問送信完了 → 無音送信（VADトリガー）")

        if self._phase == "silence":
            if self._index < len(self._silence_chunks):
                chunk = self._silence_chunks[self._index]
                self._index += 1
            else:
                self._phase = "wait"
                self._index = 0
                print("  [入力] 無音完了 → 応答待ち...")

        if self._phase == "wait":
            # 応答の音声出力が始まったら割り込みを開始
            if self._output.audio_event_count >= 5:
                self._phase = "interrupt"
                self._index = 0
                print("  🎤 [割り込み開始] エージェント応答中に割り込み音声を送信！")

        if self._phase == "interrupt":
            if self._index < len(self._interrupt_chunks):
                chunk = self._interrupt_chunks[self._index]
                self._index += 1
                if self._index == len(self._interrupt_chunks):
                    self._interrupt_sent = True
            else:
                self._phase = "interrupt_silence"
                self._index = 0
                print("  [入力] 割り込み音声送信完了 → 無音送信")

        if self._phase == "interrupt_silence":
            if self._index < len(self._interrupt_silence):
                chunk = self._interrupt_silence[self._index]
                self._index += 1
            else:
                self._phase = "done"

        if chunk is None:
            chunk = b"\x00" * CHUNK_SIZE

        await asyncio.sleep(CHUNK_MS / 1000)
        audio_b64 = base64.b64encode(chunk).decode("ascii")
        return BidiAudioInputEvent(audio=audio_b64, format="pcm", sample_rate=SAMPLE_RATE, channels=CHANNELS)

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass


class BargeInOutput:
    """割り込みイベントに注目した出力ハンドラ。"""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.audio_event_count = 0
        self.interruption_detected = False
        self.transcript_parts: list[str] = []
        self._response_count = 0

    async def __call__(self, event: BidiOutputEvent) -> None:
        event_type = type(event).__name__

        if isinstance(event, BidiTranscriptStreamEvent):
            role = getattr(event, "role", "?")
            text = getattr(event, "text", "")
            is_final = getattr(event, "is_final", False)
            if is_final:
                print(f"  [確定] ({role}): {text}")
                self.transcript_parts.append(f"({role}): {text}")
            else:
                # 途中トランスクリプトは長くなるので先頭だけ
                if len(text) < 80:
                    print(f"  [途中] ({role}): {text}")
        elif isinstance(event, BidiAudioStreamEvent):
            self.audio_event_count += 1
            if self.audio_event_count <= 3:
                print(f"  [音声出力] chunk #{self.audio_event_count}")
            elif self.audio_event_count == 4:
                print(f"  [音声出力] ... (以降省略)")
        elif "Interruption" in event_type:
            self.interruption_detected = True
            print(f"  ⚡ [割り込み検出!] {event_type}: {event}")
        elif "ResponseStart" in event_type:
            self._response_count += 1
            print(f"  [ResponseStart #{self._response_count}]")
        elif "ResponseComplete" in event_type:
            print(f"  [ResponseComplete]")
        elif "Error" in event_type:
            print(f"  ❌ [{event_type}] {event}")
        elif "Connection" in event_type:
            print(f"  [{event_type}]")

        self.events.append(event_type)

    async def start(self, agent) -> None:
        pass

    async def stop(self) -> None:
        pass


async def main() -> None:
    print("=" * 60)
    print("割り込み（barge-in）テスト")
    print("=" * 60)
    print("シナリオ: 長い質問→応答開始後に割り込み音声を送信")
    print()

    session = boto3.Session(profile_name="sandbox", region_name="us-east-1")

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
        system_prompt="あなたは日本語の音声アシスタントです。質問には丁寧に詳しく答えてください。",
    )

    output_handler = BargeInOutput()
    audio_input = BargeInAudioInput(
        question_pcm="/tmp/test_long.pcm",
        interrupt_pcm="/tmp/test_interrupt.pcm",
        output_handler=output_handler,
    )

    print("-" * 60)

    try:
        await asyncio.wait_for(
            agent.run(inputs=[audio_input], outputs=[output_handler]),
            timeout=45,
        )
    except asyncio.TimeoutError:
        print("\n  --- 45秒タイムアウト ---")

    print()
    print("=" * 60)
    print("テスト結果")
    print("=" * 60)
    print(f"  割り込み検出 (BidiInterruptionEvent): {'✅ あり' if output_handler.interruption_detected else '❌ なし'}")
    print(f"  受信イベント数: {len(output_handler.events)}")
    print(f"  音声出力チャンク数: {output_handler.audio_event_count}")
    event_types = set(output_handler.events)
    print(f"  イベント種類: {event_types}")
    if output_handler.transcript_parts:
        print(f"  トランスクリプト:")
        for t in output_handler.transcript_parts:
            print(f"    → {t}")


if __name__ == "__main__":
    asyncio.run(main())
