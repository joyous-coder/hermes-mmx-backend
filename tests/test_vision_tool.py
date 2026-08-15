"""Tests for the mmx vision describe tool handler."""

from __future__ import annotations

import json
from unittest import mock

from mmx_backends import vision_tool as vt_module


class TestVisionDescribeSchema:
    def test_schema(self):
        s = vt_module.MMX_VISION_DESCRIBE_SCHEMA
        assert s["name"] == "mmx_vision_describe"
        assert "image" in s["parameters"]["required"]
        assert s["parameters"]["properties"]["image"]["type"] == "string"


class TestHandleMmxVisionDescribe:
    def test_missing_mmx(self, mmx_missing):
        parsed = json.loads(
            vt_module._handle_mmx_vision_describe({"image": "x.jpg"})
        )
        assert "error" in parsed

    def test_missing_image_arg(self, mmx_available):
        parsed = json.loads(vt_module._handle_mmx_vision_describe({}))
        assert "error" in parsed
        assert "image" in parsed["error"]

    def test_local_file_not_found(self, mmx_available):
        parsed = json.loads(
            vt_module._handle_mmx_vision_describe(
                {"image": "C:/nonexistent/file.jpg"}
            )
        )
        assert "error" in parsed
        assert "not found" in parsed["error"]

    def test_success_returns_description(self, mmx_available, tmp_path):
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0")

        fake = mock.Mock(
            returncode=0,
            stdout="A photo of a cat sitting on a windowsill.",
            stderr="",
        )
        with mock.patch.object(vt_module, "run_mmx", return_value=fake):
            parsed = json.loads(
                vt_module._handle_mmx_vision_describe(
                    {"image": str(img), "prompt": "What is in this image?"}
                )
            )

        assert parsed["success"] is True
        assert "cat" in parsed["description"]
        assert parsed["prompt"] == "What is in this image?"

    def test_url_input_accepted(self, mmx_available):
        fake = mock.Mock(returncode=0, stdout="A landscape.", stderr="")
        with mock.patch.object(vt_module, "run_mmx", return_value=fake) as m:
            parsed = json.loads(
                vt_module._handle_mmx_vision_describe(
                    {"image": "https://example.com/cat.jpg"}
                )
            )

        assert parsed["success"] is True
        cmd_passed = m.call_args[0][0]
        assert "https://example.com/cat.jpg" in cmd_passed