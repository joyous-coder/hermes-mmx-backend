"""mmx TTSProvider — replaces text_to_speech via mmx speech synthesize.

Wraps ``mmx speech synthesize --text <text> --out <path>``. Default
model is ``speech-2.8-hd`` with optional ``speech-2.6`` / ``speech-02``.

NOTE: hermes already has a built-in TTS provider named ``minimax`` that
calls the same backend via HTTP. Our plugin uses ``mmx-cli`` to
subprocess the call instead — useful when the user prefers shelling out
(consistent with how image/video go through mmx), or when the built-in
provider can't reach the API for some reason.

Built-in providers always win at dispatch time, so setting
``tts.provider: "mmx"`` will only route here if no built-in ``minimax``
or command-type ``tts.mmx_backends.mmx`` block is active.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from agent.tts_provider import (
    DEFAULT_OUTPUT_FORMAT,
    TTSProvider,
)

from ._mmx_runner import is_mmx_available, run_mmx

logger = logging.getLogger(__name__)


class MMXTTSProvider(TTSProvider):
    """mmx-cli speech synthesize backend."""

    @property
    def name(self) -> str:
        return "mmx"

    @property
    def display_name(self) -> str:
        return "MiniMax (mmx-cli) speech-2.8-hd"

    def is_available(self) -> bool:
        return is_mmx_available()

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "speech-2.8-hd", "display": "Speech 2.8 HD", "max_text_length": 10000},
            {"id": "speech-2.6", "display": "Speech 2.6", "max_text_length": 10000},
            {"id": "speech-02", "display": "Speech 0.2", "max_text_length": 10000},
        ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "MiniMax (mmx-cli)",
            "badge": "bundled",
            "tag": "mmx speech synthesize (speech-2.8-hd by default).",
            "env_vars": [],
        }

    def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        speed: Optional[float] = None,
        format: str = DEFAULT_OUTPUT_FORMAT,
        **extra: Any,
    ) -> str:
        """Run ``mmx speech synthesize`` and return the written path.

        mmx's --out writes to the file path; we then verify it exists.
        """
        chosen_model = model or "speech-2.8-hd"

        cmd = [
            "speech", "synthesize",
            "--text", text,
            "--model", chosen_model,
            "--format", format,
            "--out", output_path,
            "--quiet",
        ]
        if voice:
            cmd.extend(["--voice", voice])
        if speed is not None:
            cmd.extend(["--speed", str(speed)])

        try:
            result = run_mmx(cmd, timeout=120)
        except RuntimeError as exc:
            logger.warning("mmx speech synthesize failed: %s", exc)
            raise RuntimeError(str(exc)) from exc

        if result.returncode != 0:
            raise RuntimeError(
                f"mmx speech synthesize failed (exit {result.returncode}): "
                f"{(result.stderr or '').strip()}"
            )

        if not os.path.exists(output_path):
            raise RuntimeError(
                f"mmx speech synthesize reported success but {output_path} not found. "
                f"stdout: {(result.stdout or '')[:200]!r}"
            )

        return output_path