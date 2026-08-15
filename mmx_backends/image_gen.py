"""mmx ImageGenProvider — replaces image_generate via mmx image generate.

Wraps ``mmx image generate --prompt <text>``. mmx's default model is
``image-01`` (text-to-image only — no image-to-image / reference image
support in image-01, so we advertise text-only modalities).

For URL or local file output we always download to disk and return the
absolute path; mmx returns a URL by default which we curl-fetch.

Note: The default OpenAI image backend is gpt-image-2 which supports
image-to-image; mmx's image-01 doesn't. Users needing image-to-image
should keep OpenAI as the image_gen.provider and use mmx only for
text-to-image. We surface this in capabilities() so the dynamic schema
hides ``image_url`` when mmx is active.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    success_response,
    error_response,
)
from agent.secret_scope import get_secret

from ._mmx_runner import is_mmx_available, run_mmx

logger = logging.getLogger(__name__)


class MMXImageGenProvider(ImageGenProvider):
    """mmx-cli image generate — text-to-image only (image-01 model)."""

    @property
    def name(self) -> str:
        return "mmx"

    @property
    def display_name(self) -> str:
        return "MiniMax (mmx-cli) image-01"

    def is_available(self) -> bool:
        return is_mmx_available()

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text"],   # image-01 doesn't do image-to-image
            "max_reference_images": 0,
        }

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "image-01",
                "display": "image-01",
                "speed": "~15s",
                "strengths": "MiniMax native text-to-image model",
            }
        ]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "MiniMax (mmx-cli)",
            "badge": "bundled",
            "tag": "mmx image generate (text-to-image, image-01).",
            "env_vars": [],
        }

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate an image. mmx image-01 does not support image-to-image;
        if ``image_url`` is supplied we route to the OpenAI backend by
        returning a clean error so the caller can switch mmx_backends.
        """
        # mmx image-01 is text-only — surface a clear error rather than
        # silently ignoring the source image.
        if image_url or reference_image_urls:
            return error_response(
                error=(
                    "mmx image-01 backend does not support image-to-image / editing. "
                    "Switch image_gen.provider to 'openai' for that capability."
                ),
                error_type="capability_not_supported",
            )

        # Resolve cache dir (matches the convention used by other providers
        # so images show up in $HERMES_HOME/cache/images/).
        try:
            from hermes_constants import get_hermes_home
            cache_dir = get_hermes_home() / "cache" / "images"
            cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            cache_dir = Path(os.path.expanduser("~")) / ".cache" / "mmx-images"
            cache_dir.mkdir(parents=True, exist_ok=True)

        out_prefix = cache_dir / f"mmx_{uuid.uuid4().hex[:8]}"

        # mmx expects --aspect-ratio as W:H (16:9, 1:1, 9:16) — translate
        # our landscape/portrait/square vocabulary to those ratios.
        aspect_map = {
            "landscape": "16:9",
            "portrait": "9:16",
            "square": "1:1",
        }
        ar = aspect_map.get(aspect_ratio, aspect_ratio)

        cmd = [
            "image", "generate",
            "--prompt", prompt,
            "--aspect-ratio", ar,
            "--out-dir", str(cache_dir),
            "--out-prefix", out_prefix.name,
            "--quiet",
            "--response-format", "url",
        ]

        try:
            result = run_mmx(cmd, timeout=180)
        except RuntimeError as exc:
            logger.warning("mmx image_generate failed: %s", exc)
            return error_response(error=str(exc))

        if result.returncode != 0:
            return error_response(
                error=(
                    f"mmx image_generate failed (exit {result.returncode}): "
                    f"{(result.stderr or '').strip()}"
                )
            )

        # mmx --quiet --response-format url prints a URL per line on stdout.
        # With --out-dir + --out-prefix the file is also written to disk.
        image_path = self._find_written_file(cache_dir, out_prefix.name)
        image_url_returned = self._first_url((result.stdout or "").strip().splitlines())

        if image_path:
            return success_response(
                image=str(image_path),
                model="image-01",
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                modality="text",
                provider=self.name,
                extra={"url": image_url_returned} if image_url_returned else {},
            )

        if image_url_returned:
            # mmx returned a URL but didn't write a file (e.g. permission
            # issue). Surface the URL so the caller can fetch it.
            return success_response(
                image=image_url_returned,
                model="image-01",
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                modality="text",
                provider=self.name,
            )

        return error_response(
            error=(
                f"mmx image_generate produced no output. stdout: "
                f"{(result.stdout or '')[:200]!r}"
            )
        )

    @staticmethod
    def _find_written_file(cache_dir: Path, prefix: str) -> Optional[str]:
        """Return the most recent file in cache_dir starting with ``prefix``."""
        try:
            candidates = sorted(
                cache_dir.glob(f"{prefix}*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return None
        for cand in candidates:
            if cand.is_file():
                return str(cand.resolve())
        return None

    @staticmethod
    def _first_url(lines: List[str]) -> Optional[str]:
        for line in lines:
            line = line.strip()
            if line.startswith(("http://", "https://")):
                return line
        return None