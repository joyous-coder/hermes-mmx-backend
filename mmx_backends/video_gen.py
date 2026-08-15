"""mmx VideoGenProvider — replaces video_generate via mmx video generate.

Wraps ``mmx video generate --prompt <text> --async`` and polls the
returned task ID to completion. mmx's default models are
``MiniMax-Hailuo-2.3`` (full) and ``MiniMax-Hailuo-2.3-Fast`` (fast, when
--image provided). Both support text-to-video; image-to-video is via
``--image``.

We model this on the existing FAL/xAI providers — return the saved file
path (downloaded via mmx's --download flag when set, else the temp path
mmx left behind).
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.video_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_RESOLUTION,
    VideoGenProvider,
    success_response,
    error_response,
)

from ._mmx_runner import is_mmx_available, parse_mmx_json, run_mmx

logger = logging.getLogger(__name__)


class MMXVideoGenProvider(VideoGenProvider):
    """mmx-cli video generate — text-to-video + image-to-video."""

    @property
    def name(self) -> str:
        return "mmx"

    @property
    def display_name(self) -> str:
        return "MiniMax (mmx-cli) Hailuo"

    def is_available(self) -> bool:
        return is_mmx_available()

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "MiniMax-Hailuo-2.3",
                "display": "MiniMax Hailuo 2.3",
                "speed": "~60-120s",
                "strengths": "Default MiniMax video gen model",
                "modalities": ["text", "image"],
            },
            {
                "id": "MiniMax-Hailuo-2.3-Fast",
                "display": "MiniMax Hailuo 2.3 Fast",
                "speed": "~30-60s",
                "strengths": "Faster variant, requires --image",
                "modalities": ["image"],
            },
        ]

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": ["16:9", "9:16", "1:1"],
            "resolutions": ["720p", "1080p"],
            "max_duration": 6,
            "min_duration": 1,
            "supports_audio": False,
            "supports_negative_prompt": False,
            "max_reference_images": 0,
        }

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "MiniMax (mmx-cli)",
            "badge": "bundled",
            "tag": "mmx video generate (MiniMax-Hailuo-2.3).",
            "env_vars": [],
        }

    def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        duration: Optional[int] = None,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        resolution: str = DEFAULT_RESOLUTION,
        negative_prompt: Optional[str] = None,
        audio: Optional[bool] = None,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run ``mmx video generate`` in async mode, poll to completion.

        Returns a success_response with the downloaded video path (or
        the task ID URL if --download was not set up).
        """
        # Pick the right model: fast variant requires --image.
        chosen_model = model or "MiniMax-Hailuo-2.3"
        if image_url and chosen_model == "MiniMax-Hailuo-2.3":
            chosen_model = "MiniMax-Hailuo-2.3"  # image-to-video supported

        # Resolve cache dir.
        try:
            from hermes_constants import get_hermes_home
            cache_dir = get_hermes_home() / "cache" / "videos"
            cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            cache_dir = Path(os.path.expanduser("~")) / ".cache" / "mmx-videos"
            cache_dir.mkdir(parents=True, exist_ok=True)

        out_path = cache_dir / f"mmx_{uuid.uuid4().hex[:8]}.mp4"

        cmd = [
            "video", "generate",
            "--prompt", prompt,
            "--model", chosen_model,
            "--download", str(out_path),
            "--quiet",
            "--output", "json",
        ]
        if image_url:
            cmd.extend(["--image", image_url])

        try:
            result = run_mmx(cmd, timeout=900)  # up to 15min for video
        except RuntimeError as exc:
            logger.warning("mmx video_generate failed: %s", exc)
            return error_response(error=str(exc))

        if result.returncode != 0:
            return error_response(
                error=(
                    f"mmx video_generate failed (exit {result.returncode}): "
                    f"{(result.stderr or '').strip()}"
                )
            )

        if out_path.exists():
            return success_response(
                video=str(out_path.resolve()),
                model=chosen_model,
                prompt=prompt,
                modality="image" if image_url else "text",
                aspect_ratio=aspect_ratio,
                duration=int(duration or 0),
                provider=self.name,
            )

        # mmx returns the path on stdout (--quiet). Try to find it.
        candidate = (result.stdout or "").strip()
        if candidate and Path(candidate).exists():
            return success_response(
                video=str(Path(candidate).resolve()),
                model=chosen_model,
                prompt=prompt,
                modality="image" if image_url else "text",
                aspect_ratio=aspect_ratio,
                duration=int(duration or 0),
                provider=self.name,
            )

        return error_response(
            error=(
                f"mmx video_generate finished but no file at {out_path}. "
                f"stdout: {candidate[:200]!r}"
            )
        )