"""Pytest config for hermes-mmx-backend tests.

This test environment runs against the user's hermes-agent install
(C:\\Users\\20466\\AppData\\Local\\hermes\\hermes-agent on PYTHONPATH),
so the real ``agent.*`` ABCs and ``tools.registry`` helpers are used.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture
def mmx_available(monkeypatch):
    """Patch mmx CLI to appear installed and responsive.

    - ``shutil.which("mmx")`` returns ``/usr/bin/mmx``
    - ``subprocess.run(["/usr/bin/mmx", "--version"], ...)`` returns exit 0

    Implementation note: patching a *function* (subprocess.run) with a
    bare Mock() makes calls return a child Mock — so ``.returncode`` ends
    up as ``<Mock name='mock().returncode'>`` instead of 0. The fix is
    to wrap a real ``subprocess.CompletedProcess`` as the Mock's
    ``return_value``.
    """
    from unittest import mock

    from mmx_backends import _mmx_runner

    monkeypatch.setattr(_mmx_runner.shutil, "which", lambda _: "/usr/bin/mmx")
    cp = subprocess.CompletedProcess(
        args=["mmx", "--version"], returncode=0,
        stdout="MiniMax CLI 1.0.16", stderr="",
    )
    fake = mock.Mock(return_value=cp)
    monkeypatch.setattr(_mmx_runner.subprocess, "run", value=fake)
    return _mmx_runner


@pytest.fixture
def mmx_missing(monkeypatch):
    """Patch mmx CLI to appear absent (``shutil.which`` returns None)."""
    from mmx_backends import _mmx_runner

    monkeypatch.setattr(_mmx_runner.shutil, "which", lambda _: None)
    return _mmx_runner