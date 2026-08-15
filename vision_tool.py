"""mmx vision describe — standalone tool (no hermes vision ABC exists).

Wraps ``mmx vision describe --image <path-or-url>``. Default VLM is
mmx's multimodal VLM. Output is a text description answering ``prompt``.

Hermes already has ``vision_analyze`` (a built-in tool) but that uses
the configured chat model for image understanding. mmx vision uses a
dedicated MiniMax multimodal model — potentially better at OCR / fine
visual detail, and doesn't burn chat-model tokens.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

from tools.registry import tool_error, tool_result

from _mmx_runner import is_mmx_available, run_mmx

logger = logging.getLogger(__name__)


MMX_VISION_DESCRIBE_SCHEMA: Dict[str, Any] = {
    "name": "mmx_vision_describe",
    "description": (
        "Describe an image using the MiniMax multimodal vision model via "
        "mmx-cli. Provide either a local file path or an HTTP(S) URL. "
        "Use this instead of the built-in vision_analyze when you need "
        "OCR-grade detail or want to avoid burning chat-model tokens."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "image": {
                "type": "string",
                "description": "Local file path or http(s) URL of the image.",
            },
            "prompt": {
                "type": "string",
                "default": "Describe the image.",
                "description": "What to extract / describe from the image.",
            },
        },
        "required": ["image"],
    },
}


def _is_url(s: str) -> bool:
    return s.lower().startswith(("http://", "https://"))


def _handle_mmx_vision_describe(args: Dict[str, Any], **kwargs: Any) -> str:
    """Run ``mmx vision describe`` and return the textual description."""
    if not is_mmx_available():
        return tool_error("mmx CLI not found in PATH. Install: uv tool install mmx-cli")

    image = args.get("image")
    if not image:
        return tool_error("mmx_vision_describe requires an `image` (path or URL).")

    if not _is_url(image) and not Path(image).exists():
        return tool_error(f"Local image not found: {image}")

    prompt = args.get("prompt") or "Describe the image."

    cmd = [
        "vision", "describe",
        "--image", image,
        "--prompt", prompt,
        "--output", "json",
        "--quiet",
    ]

    try:
        result = run_mmx(cmd, timeout=120)
    except RuntimeError as exc:
        logger.warning("mmx vision describe failed: %s", exc)
        return tool_error(str(exc))

    if result.returncode != 0:
        return tool_error(
            f"mmx vision describe failed (exit {result.returncode}): "
            f"{(result.stderr or '').strip()}"
        )

    description = (result.stdout or "").strip()
    payload = {
        "success": True,
        "description": description,
        "image": image,
        "prompt": prompt,
        "provider": "mmx",
    }
    return tool_result(payload)