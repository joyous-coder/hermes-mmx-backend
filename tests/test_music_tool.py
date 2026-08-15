"""Tests for the mmx music generate tool handler."""

from __future__ import annotations

import json
from unittest import mock

import music_tool as mt_module


class TestMusicGenerateSchema:
    def test_schema_has_required_prompt(self):
        schema = mt_module.MMX_MUSIC_GENERATE_SCHEMA
        assert schema["name"] == "mmx_music_generate"
        assert "prompt" in schema["parameters"]["required"]
        assert "lyrics" in schema["parameters"]["properties"]
        assert "instrumental" in schema["parameters"]["properties"]


class TestHandleMmxMusicGenerate:
    def test_missing_mmx_returns_error(self, mmx_missing):
        result = mt_module._handle_mmx_music_generate({"prompt": "test"})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "mmx CLI not found" in parsed["error"]

    def test_requires_prompt_or_lyrics_or_instrumental(self, mmx_available):
        result = mt_module._handle_mmx_music_generate({})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "requires" in parsed["error"].lower()

    def test_success_with_written_file(self, mmx_available, tmp_path, monkeypatch):
        # Force the default output dir to tmp_path so the file lands
        # inside our writable scratch area.
        monkeypatch.setattr(mt_module, "_default_music_dir", lambda: tmp_path)

        written = tmp_path / "out.mp3"
        written.write_bytes(b"fake-mp3")

        fake_result = mock.Mock(returncode=0, stdout=str(written), stderr="")
        with mock.patch.object(mt_module, "run_mmx", return_value=fake_result):
            result = mt_module._handle_mmx_music_generate(
                {"prompt": "Upbeat pop", "lyrics": "la la la"}
            )
            parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsed.get("lyrics_provided") is True
        assert parsed.get("instrumental") is False

    def test_subprocess_error_envelope(self, mmx_available):
        fake_result = mock.Mock(returncode=1, stdout="", stderr="quota exceeded")
        with mock.patch.object(mt_module, "run_mmx", return_value=fake_result):
            result = mt_module._handle_mmx_music_generate({"prompt": "x"})
            parsed = json.loads(result)
        assert "error" in parsed
        assert "quota exceeded" in parsed["error"]