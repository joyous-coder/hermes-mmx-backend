"""Tests for the mmx ImageGenProvider.

Uses the real hermes-agent ABC. Mocks subprocess.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest import mock

import image_gen as ig_module


class TestImageGenProviderBasics:
    def _provider(self):
        return ig_module.MMXImageGenProvider()

    def test_name_and_capabilities(self):
        p = self._provider()
        assert p.name == "mmx"
        caps = p.capabilities()
        # mmx image-01 is text-only — no image-to-image.
        assert caps["modalities"] == ["text"]

    def test_is_available_when_mmx_missing(self, mmx_missing):
        assert self._provider().is_available() is False

    def test_image_to_image_rejected_with_capability_error(self, mmx_available):
        result = self._provider().generate(
            "edit this",
            aspect_ratio="square",
            image_url="https://example.com/x.jpg",
        )
        assert result["success"] is False
        assert result.get("error_type") == "capability_not_supported"
        assert "does not support image-to-image" in result["error"]


class TestImageGenAspectRatio:
    def test_landscape_to_16_9(self, mmx_available, tmp_path):
        captured = {}

        def fake_run(cmd, *args, **kwargs):
            captured["cmd"] = cmd
            try:
                idx = cmd.index("--out-prefix")
                prefix = cmd[idx + 1]
                idx2 = cmd.index("--out-dir")
                out_dir = Path(cmd[idx2 + 1])
                fake_file = out_dir / f"{prefix}_0.png"
                fake_file.write_bytes(b"\x89PNG\r\n\x1a\n")
            except Exception:
                pass
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(ig_module, "run_mmx", side_effect=fake_run):
            # Override cache_dir via hermes_constants.
            fake_const = types.ModuleType("hermes_constants")
            fake_const.get_hermes_home = lambda: tmp_path
            sys.modules["hermes_constants"] = fake_const

            result = ig_module.MMXImageGenProvider().generate(
                "a sunset", aspect_ratio="landscape"
            )

        assert "--aspect-ratio" in captured["cmd"]
        i = captured["cmd"].index("--aspect-ratio")
        assert captured["cmd"][i + 1] == "16:9"
        assert result.get("success") is True
        assert result.get("image")