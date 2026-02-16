"""config.py のユニットテスト"""

import os
from unittest.mock import patch

from config import get_model, SYSTEM_PROMPT


class TestSystemPrompt:
    def test_prompt_is_japanese(self):
        assert "日本語" in SYSTEM_PROMPT

    def test_prompt_mentions_tools(self):
        assert "ツール" in SYSTEM_PROMPT

    def test_prompt_mentions_stop(self):
        assert "stop_conversation" in SYSTEM_PROMPT


class TestGetModel:
    def test_returns_model_instance(self):
        model = get_model()
        assert model is not None

    def test_default_region(self):
        model = get_model()
        assert model.region == "us-east-1"

    def test_custom_region_from_env(self):
        with patch.dict(os.environ, {"NOVA_SONIC_REGION": "eu-north-1"}):
            model = get_model()
            assert model.region == "eu-north-1"

    def test_default_voice(self):
        model = get_model()
        assert model.config["audio"]["voice"] == "tiffany"

    def test_custom_voice_from_env(self):
        with patch.dict(os.environ, {"NOVA_SONIC_VOICE": "matthew"}):
            model = get_model()
            assert model.config["audio"]["voice"] == "matthew"

    def test_sample_rate_16k(self):
        model = get_model()
        assert model.config["audio"]["input_sample_rate"] == 16000
        assert model.config["audio"]["output_sample_rate"] == 16000
