"""agent.py の WebSocketBidiInput/Output ユニットテスト"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import WebSocketBidiInput, WebSocketBidiOutput


class TestWebSocketBidiInput:
    @pytest.mark.asyncio
    async def test_returns_audio_event(self):
        ws = AsyncMock()
        ws.receive_json = AsyncMock(return_value={
            "type": "audio",
            "audio": "dGVzdA==",  # "test" in base64
        })

        input_ = WebSocketBidiInput(ws)
        event = await input_()

        assert event.audio == "dGVzdA=="
        assert event.format == "pcm"
        assert event.sample_rate == 16000
        assert event.channels == 1

    @pytest.mark.asyncio
    async def test_skips_non_audio_messages(self):
        ws = AsyncMock()
        call_count = 0

        async def receive_json_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"type": "ping"}
            return {"type": "audio", "audio": "AAAA"}

        ws.receive_json = AsyncMock(side_effect=receive_json_side_effect)

        input_ = WebSocketBidiInput(ws)
        event = await input_()

        assert event.audio == "AAAA"
        assert ws.receive_json.call_count == 2

    @pytest.mark.asyncio
    async def test_start_and_stop_are_noop(self):
        ws = AsyncMock()
        input_ = WebSocketBidiInput(ws)
        await input_.start(MagicMock())
        await input_.stop()


class TestWebSocketBidiOutput:
    @pytest.mark.asyncio
    async def test_sends_audio_event(self):
        ws = AsyncMock()
        output = WebSocketBidiOutput(ws)

        event = {"type": "bidi_audio_stream", "audio": "AQID"}
        await output(event)

        ws.send_json.assert_called_once()
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "audio"
        assert sent["audio"] == "AQID"

    @pytest.mark.asyncio
    async def test_sends_transcript_event(self):
        ws = AsyncMock()
        output = WebSocketBidiOutput(ws)

        event = {
            "type": "bidi_transcript_stream",
            "role": "assistant",
            "text": "こんにちは",
            "is_final": True,
        }
        await output(event)

        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "transcript"
        assert sent["role"] == "assistant"
        assert sent["text"] == "こんにちは"
        assert sent["is_final"] is True

    @pytest.mark.asyncio
    async def test_sends_interruption_event(self):
        ws = AsyncMock()
        output = WebSocketBidiOutput(ws)

        await output({"type": "bidi_interruption", "reason": "user_speech"})

        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "interruption"

    @pytest.mark.asyncio
    async def test_sends_tool_use_event(self):
        ws = AsyncMock()
        output = WebSocketBidiOutput(ws)

        event = {
            "type": "tool_use_stream",
            "current_tool_use": {"name": "get_current_time", "toolUseId": "123", "input": {}},
        }
        await output(event)

        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "tool_use"
        assert sent["name"] == "get_current_time"

    @pytest.mark.asyncio
    async def test_sends_error_event(self):
        ws = AsyncMock()
        output = WebSocketBidiOutput(ws)

        await output({"type": "bidi_error", "message": "Something failed"})

        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "error"
        assert sent["message"] == "Something failed"

    @pytest.mark.asyncio
    async def test_ignores_unknown_event(self):
        ws = AsyncMock()
        output = WebSocketBidiOutput(ws)

        await output({"type": "bidi_usage", "inputTokens": 10})

        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_send_failure_gracefully(self):
        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("connection closed"))
        output = WebSocketBidiOutput(ws)

        # Should not raise
        await output({"type": "bidi_audio_stream", "audio": "data"})

    @pytest.mark.asyncio
    async def test_start_and_stop_are_noop(self):
        ws = AsyncMock()
        output = WebSocketBidiOutput(ws)
        await output.start(MagicMock())
        await output.stop()
