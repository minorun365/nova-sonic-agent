"""Voice Agent - WebSocket + BidiAgent ブリッジ"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.types.events import BidiAudioInputEvent
from strands.experimental.bidi.tools import stop_conversation

from config import get_model, SYSTEM_PROMPT
from tools import get_current_time, simple_calculator

app = BedrockAgentCoreApp()


class WebSocketBidiInput:
    """WebSocket からの音声データを BidiAudioInputEvent に変換"""

    def __init__(self, websocket):
        self.websocket = websocket

    async def start(self, agent):
        pass

    async def stop(self):
        pass

    async def __call__(self):
        while True:
            data = await self.websocket.receive_json()
            if data.get("type") == "audio":
                return BidiAudioInputEvent(
                    audio=data["audio"],
                    format="pcm",
                    sample_rate=16000,
                    channels=1,
                )


class WebSocketBidiOutput:
    """BidiAgent のイベントを WebSocket でブラウザに送信"""

    def __init__(self, websocket):
        self.websocket = websocket

    async def start(self, agent):
        pass

    async def stop(self):
        pass

    async def __call__(self, event):
        event_type = event.get("type", "") if isinstance(event, dict) else getattr(event, "type", "")

        try:
            if event_type == "bidi_audio_stream":
                audio = event["audio"] if isinstance(event, dict) else event.audio
                await self.websocket.send_json({
                    "type": "audio",
                    "audio": audio,
                })
            elif event_type == "bidi_transcript_stream":
                if isinstance(event, dict):
                    role, text, is_final = event["role"], event["text"], event.get("is_final", False)
                else:
                    role, text, is_final = event.role, event.text, getattr(event, "is_final", False)
                await self.websocket.send_json({
                    "type": "transcript",
                    "role": role,
                    "text": text,
                    "is_final": is_final,
                })
            elif event_type == "bidi_interruption":
                await self.websocket.send_json({"type": "interruption"})
            elif "tool_use" in event_type:
                tool_info = event.get("current_tool_use", {}) if isinstance(event, dict) else getattr(event, "current_tool_use", {})
                await self.websocket.send_json({
                    "type": "tool_use",
                    "name": tool_info.get("name", "unknown") if isinstance(tool_info, dict) else "unknown",
                })
            elif event_type == "bidi_error":
                msg = event.get("message", "Unknown error") if isinstance(event, dict) else getattr(event, "message", "Unknown error")
                await self.websocket.send_json({
                    "type": "error",
                    "message": str(msg),
                })
        except Exception as e:
            print(f"[WARN] Failed to send event ({event_type}): {e}")


@app.websocket
async def websocket_handler(websocket, context):
    """WebSocket ハンドラ: ブラウザ ↔ BidiAgent ブリッジ"""
    await websocket.accept()

    model = get_model()
    agent = BidiAgent(
        model=model,
        tools=[stop_conversation, get_current_time, simple_calculator],
        system_prompt=SYSTEM_PROMPT,
    )

    ws_input = WebSocketBidiInput(websocket)
    ws_output = WebSocketBidiOutput(websocket)

    try:
        await agent.run(inputs=[ws_input], outputs=[ws_output])
    except Exception as e:
        print(f"[INFO] WebSocket session ended: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    app.run()
