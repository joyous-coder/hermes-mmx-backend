"""Tests for the mmx WebSearchProvider response-shape mapping.

Uses the real hermes-agent ABC. We mock the mmx subprocess call.
"""

from __future__ import annotations

import json
from unittest import mock

from providers import _mmx_runner
from providers import web_search as ws_module


class _StubSubprocessResult:
    def __init__(self, returncode, stdout, stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestMMXWebSearchProvider:
    def _provider(self):
        return ws_module.MMXWebSearchProvider()

    def test_name_and_display(self):
        p = self._provider()
        assert p.name == "mmx"
        assert p.display_name == "MiniMax (mmx-cli)"

    def test_supports_search_only(self):
        p = self._provider()
        assert p.supports_search() is True
        assert p.supports_extract() is False

    def test_is_available_when_mmx_missing(self, monkeypatch, mmx_missing):
        p = self._provider()
        assert p.is_available() is False

    def test_search_maps_organic_results(self, monkeypatch, mmx_available):
        fake_payload = {
            "organic": [
                {
                    "title": "Example",
                    "link": "https://example.com",
                    "snippet": "An example.",
                    "date": "2026-08-15",
                },
                {
                    "title": "Second",
                    "link": "https://second.com",
                    "snippet": "Second result.",
                },
            ],
            "base_resp": {"status_code": 0},
        }
        fake_result = _StubSubprocessResult(
            returncode=0, stdout=json.dumps(fake_payload)
        )

        with mock.patch.object(ws_module, "run_mmx", return_value=fake_result):
            p = self._provider()
            result = p.search("test query", limit=5)

        assert result["success"] is True
        web = result["data"]["web"]
        assert len(web) == 2
        assert web[0]["title"] == "Example"
        assert web[0]["url"] == "https://example.com"
        assert web[0]["description"] == "An example."
        assert web[0]["position"] == 1
        assert web[1]["position"] == 2

    def test_search_empty_results_returns_success(self, monkeypatch, mmx_available):
        fake_result = _StubSubprocessResult(
            returncode=0,
            stdout=json.dumps({"organic": [], "base_resp": {"status_code": 0}}),
        )
        with mock.patch.object(ws_module, "run_mmx", return_value=fake_result):
            p = self._provider()
            result = p.search("nothing matches")

        assert result["success"] is True
        assert result["data"]["web"] == []

    def test_search_subprocess_failure_envelope(self, monkeypatch, mmx_available):
        with mock.patch.object(
            ws_module,
            "run_mmx",
            side_effect=RuntimeError("mmx CLI failed (exit 1): auth failed"),
        ):
            p = self._provider()
            result = p.search("anything")

        assert result["success"] is False
        assert "auth failed" in result["error"]

    def test_setup_schema(self):
        p = self._provider()
        schema = p.get_setup_schema()
        assert schema["name"] == "MiniMax (mmx-cli)"
        assert schema["badge"] == "bundled"