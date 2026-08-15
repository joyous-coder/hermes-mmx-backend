"""Tests for the mmx TTSProvider."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import tts as tts_module


class TestMMXTTSProvider:
    def _provider(self):
        return tts_module.MMXTTSProvider()

    def test_name(self):
        assert self._provider().name == "mmx"

    def test_default_model(self):
        models = self._provider().list_models()
        assert len(models) == 3
        assert self._provider().default_model() == "speech-2.8-hd"

    def test_is_available_when_mmx_missing(self, mmx_missing):
        assert self._provider().is_available() is False

    def test_synthesize_writes_file(self, mmx_available, tmp_path):
        out_path = tmp_path / "out.mp3"

        def fake_run(cmd, *args, **kwargs):
            idx = cmd.index("--out")
            Path(cmd[idx + 1]).write_bytes(b"ID3\x03")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(tts_module, "run_mmx", side_effect=fake_run):
            result = self._provider().synthesize(
                "hello world",
                str(out_path),
                voice="English_expressive_narrator",
            )

        assert result == str(out_path)
        assert out_path.exists()

    def test_synthesize_passes_optional_args(self, mmx_available, tmp_path):
        out_path = tmp_path / "out.mp3"
        captured = {}

        def fake_run(cmd, *args, **kwargs):
            captured["cmd"] = cmd
            out_path.write_bytes(b"x")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(tts_module, "run_mmx", side_effect=fake_run):
            self._provider().synthesize(
                "hi",
                str(out_path),
                voice="v1",
                speed=1.5,
                format="wav",
            )

        assert "--voice" in captured["cmd"]
        assert "v1" in captured["cmd"]
        assert "--speed" in captured["cmd"]
        assert "1.5" in captured["cmd"]
        assert "--format" in captured["cmd"]
        assert "wav" in captured["cmd"]

    def test_synthesize_failure_raises(self, mmx_available, tmp_path):
        with mock.patch.object(
            tts_module,
            "run_mmx",
            return_value=mock.Mock(returncode=1, stdout="", stderr="bad"),
        ):
            try:
                self._provider().synthesize("hi", str(tmp_path / "x.mp3"))
            except RuntimeError as exc:
                assert "exit 1" in str(exc)
            else:
                raise AssertionError("expected RuntimeError")