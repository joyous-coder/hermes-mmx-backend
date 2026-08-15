"""Tests for the mmx subprocess runner helpers."""

from __future__ import annotations

import json
from unittest import mock

from mmx_backends import _mmx_runner


class TestWhichMmx:
    def test_returns_none_when_missing(self, monkeypatch):
        monkeypatch.setattr(_mmx_runner.shutil, "which", lambda _: None)
        assert _mmx_runner._which_mmx() is None

    def test_returns_path_when_present(self, monkeypatch):
        monkeypatch.setattr(
            _mmx_runner.shutil, "which", lambda name: "/usr/local/bin/mmx"
        )
        assert _mmx_runner._which_mmx() == "/usr/local/bin/mmx"


class TestIsMmxAvailable:
    def test_false_when_missing(self, monkeypatch):
        monkeypatch.setattr(_mmx_runner.shutil, "which", lambda _: None)
        assert _mmx_runner.is_mmx_available() is False

    def test_false_on_nonzero_exit(self, monkeypatch):
        monkeypatch.setattr(_mmx_runner.shutil, "which", lambda _: "/usr/bin/mmx")
        fake = mock.Mock(returncode=1, stdout="", stderr="bad")
        with mock.patch.object(_mmx_runner.subprocess, "run", return_value=fake):
            assert _mmx_runner.is_mmx_available() is False

    def test_false_on_timeout(self, monkeypatch):
        monkeypatch.setattr(_mmx_runner.shutil, "which", lambda _: "/usr/bin/mmx")
        with mock.patch.object(
            _mmx_runner.subprocess, "run",
            side_effect=_mmx_runner.subprocess.TimeoutExpired(cmd="mmx", timeout=5),
        ):
            assert _mmx_runner.is_mmx_available() is False

    def test_true_on_zero_exit(self, monkeypatch):
        monkeypatch.setattr(_mmx_runner.shutil, "which", lambda _: "/usr/bin/mmx")
        fake = mock.Mock(returncode=0, stdout="MiniMax CLI 1.0.16", stderr="")
        with mock.patch.object(_mmx_runner.subprocess, "run", return_value=fake):
            assert _mmx_runner.is_mmx_available() is True


class TestParseMmxJson:
    def test_raises_on_nonzero_exit(self):
        fake = mock.Mock(returncode=1, stdout="", stderr="auth failed")
        try:
            _mmx_runner.parse_mmx_json(fake)
        except RuntimeError as exc:
            assert "exit 1" in str(exc)
            assert "auth failed" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")

    def test_parses_valid_json(self):
        fake = mock.Mock(
            returncode=0,
            stdout='{"organic": [], "base_resp": {"status_code": 0}}',
            stderr="",
        )
        result = _mmx_runner.parse_mmx_json(fake)
        assert "organic" in result
        assert result["base_resp"]["status_code"] == 0

    def test_raises_on_invalid_json(self):
        fake = mock.Mock(returncode=0, stdout="not json", stderr="")
        try:
            _mmx_runner.parse_mmx_json(fake)
        except RuntimeError as exc:
            assert "not valid JSON" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")