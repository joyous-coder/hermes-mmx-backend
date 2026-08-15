"""Tests for the mmx VideoGenProvider."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest import mock

from providers import video_gen as vg_module


class TestMMXVideoGenProvider:
    def _provider(self):
        return vg_module.MMXVideoGenProvider()

    def test_name_and_models(self):
        p = self._provider()
        assert p.name == "mmx"
        models = p.list_models()
        ids = [m["id"] for m in models]
        assert "MiniMax-Hailuo-2.3" in ids
        assert "MiniMax-Hailuo-2.3-Fast" in ids

    def test_capabilities_advertise_both_modalities(self):
        caps = self._provider().capabilities()
        assert "text" in caps["modalities"]
        assert "image" in caps["modalities"]

    def test_generate_returns_downloaded_path(self, mmx_available, tmp_path):
        # Override cache_dir via hermes_constants.
        fake_const = types.ModuleType("hermes_constants")
        fake_const.get_hermes_home = lambda: tmp_path
        sys.modules["hermes_constants"] = fake_const

        captured = {}

        def fake_run(cmd, *args, **kwargs):
            captured["cmd"] = cmd
            idx = cmd.index("--download")
            out_path = Path(cmd[idx + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"FAKE_MP4")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(vg_module, "run_mmx", side_effect=fake_run):
            result = self._provider().generate("a robot walking")

        assert result["success"] is True
        assert Path(result["video"]).exists()
        assert result["video"].endswith(".mp4")
        assert result["model"] == "MiniMax-Hailuo-2.3"

    def test_generate_image_to_video(self, mmx_available, tmp_path):
        fake_const = types.ModuleType("hermes_constants")
        fake_const.get_hermes_home = lambda: tmp_path
        sys.modules["hermes_constants"] = fake_const

        captured = {}

        def fake_run(cmd, *args, **kwargs):
            captured["cmd"] = cmd
            idx = cmd.index("--download")
            out_path = Path(cmd[idx + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"FAKE")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(vg_module, "run_mmx", side_effect=fake_run):
            result = self._provider().generate(
                "animate this", image_url="https://x.com/i.jpg"
            )

        assert result["success"] is True
        assert result["modality"] == "image"
        assert "--image" in captured["cmd"]
        assert "https://x.com/i.jpg" in captured["cmd"]

    def test_generate_no_output_returns_error(self, mmx_available, tmp_path):
        fake_const = types.ModuleType("hermes_constants")
        fake_const.get_hermes_home = lambda: tmp_path
        sys.modules["hermes_constants"] = fake_const

        with mock.patch.object(
            vg_module,
            "run_mmx",
            return_value=mock.Mock(returncode=0, stdout="", stderr=""),
        ):
            result = self._provider().generate("nothing happens")

        assert result["success"] is False