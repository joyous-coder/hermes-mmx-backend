"""Shared helpers for mmx backend providers.

Every mmx provider shells out to the ``mmx`` CLI rather than using the
MiniMax Python SDK directly. Rationale:

- ``mmx-cli`` is already installed and authenticated on the user's box;
  wrapping the CLI means we inherit its region detection, retry logic,
  output formatting, and credential persistence for free.
- mmx is small, well-tested, and the user can invoke the same commands
  from their shell for debugging — no parallel implementation to keep
  in sync.

These helpers centralize:
- subprocess invocation with consistent timeout and error envelope
- JSON output parsing with safe fallback
- availability check (``mmx --version`` + auth)
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# mmx CLI commands are generally fast (text/chat/image ~10s, video ~minutes).
# 600s is a generous ceiling for the slowest video generation task.
DEFAULT_TIMEOUT = 600


def _which_mmx() -> Optional[str]:
    """Return path to mmx binary, or None if not in PATH."""
    return shutil.which("mmx")


def is_mmx_available() -> bool:
    """Return True if ``mmx`` is in PATH and responds to ``--version``.

    Cheap check suitable for provider ``is_available()``. Does NOT make
    network calls — auth status is verified lazily on first real call.
    """
    binary = _which_mmx()
    if not binary:
        return False
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("mmx --version failed: %s", exc)
        return False


def run_mmx(
    args: List[str],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    input_bytes: Optional[bytes] = None,
    binary: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """Run an ``mmx`` CLI command, returning the CompletedProcess.

    Always uses ``shell=False`` (argv list) so user-supplied values can't
    inject shell metacharacters. Caller should pass explicit
    ``--output json`` when they need machine-readable output.

    ``input_bytes`` is used when piping image bytes (vision describe
    with a local file path is preferred; this exists for forward compat).
    """
    mmx_bin = binary or _which_mmx()
    if not mmx_bin:
        raise RuntimeError(
            "mmx CLI not found in PATH. Install with: uv tool install mmx-cli"
        )
    return subprocess.run(
        [mmx_bin, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        input=input_bytes.decode("utf-8") if input_bytes else None,
    )


def parse_mmx_json(result: subprocess.CompletedProcess) -> Dict[str, Any]:
    """Parse ``mmx --output json`` stdout, raising a clear error on failure.

    ``mmx`` prints a single JSON object on success; ``--quiet`` doesn't
    affect that flag combination. On failure, ``stderr`` carries a human-
    readable error — we surface it verbatim.
    """
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"mmx CLI failed (exit {result.returncode}): {stderr or 'no stderr'}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"mmx output not valid JSON: {exc}; raw: {result.stdout[:200]!r}"
        ) from exc