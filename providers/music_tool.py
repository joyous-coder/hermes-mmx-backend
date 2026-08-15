"""mmx music generate — standalone tool (no hermes music ABC exists).

Hermes Agent has no music-generation provider ABC today, so we register
``mmx_music_generate`` as a standalone tool via ``ctx.register_tool``.

Wraps ``mmx music generate``. Default model is ``music-3.0``. Supports
both lyrics-driven and instrumental generation; long structured prompts
respond well.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import tool_error, tool_result

from ._mmx_runner import is_mmx_available, run_mmx

logger = logging.getLogger(__name__)


MMX_MUSIC_GENERATE_SCHEMA: Dict[str, Any] = {
    "name": "mmx_music_generate",
    "description": (
        "Generate music via the MiniMax music-3.0 model. Provide either "
        "lyrics (with structure tags) OR set instrumental=true for a "
        "no-vocals track. Optional: genre, mood, instruments, tempo, bpm, "
        "vocals style, references to similar artists."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Music style description (e.g. 'Upbeat folk about summer').",
            },
            "lyrics": {
                "type": "string",
                "description": "Song lyrics with structure tags. Omit for instrumental.",
            },
            "instrumental": {
                "type": "boolean",
                "default": False,
                "description": "Generate instrumental music (no vocals). Mutually exclusive with lyrics.",
            },
            "vocals": {
                "type": "string",
                "description": "Vocal style hint, e.g. 'warm male baritone' or 'duet with harmonies'.",
            },
            "genre": {"type": "string"},
            "mood": {"type": "string"},
            "instruments": {"type": "string"},
            "tempo": {"type": "string", "description": "e.g. fast / moderate / slow"},
            "bpm": {"type": "integer"},
            "key": {"type": "string"},
            "avoid": {"type": "string"},
            "use_case": {"type": "string"},
            "structure": {"type": "string"},
            "references": {"type": "string", "description": "Similar artists/tracks."},
            "lyrics_optimizer": {
                "type": "boolean",
                "default": False,
                "description": "Auto-generate lyrics from prompt (mutually exclusive with lyrics/instrumental).",
            },
            "output_path": {
                "type": "string",
                "description": "Override the auto-generated output path. Defaults to $HERMES_HOME/cache/music/.",
            },
        },
        "required": ["prompt"],
    },
}


def _default_music_dir() -> Path:
    try:
        from hermes_constants import get_hermes_home
        cache = get_hermes_home() / "cache" / "music"
    except Exception:
        cache = Path(os.path.expanduser("~")) / ".cache" / "mmx-music"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _handle_mmx_music_generate(args: Dict[str, Any], **kwargs: Any) -> str:
    """Run ``mmx music generate`` and return a JSON envelope."""
    if not is_mmx_available():
        return tool_error("mmx CLI not found in PATH. Install: uv tool install mmx-cli")

    prompt = args.get("prompt")
    if not prompt and not args.get("lyrics") and not args.get("instrumental") and not args.get("lyrics_optimizer"):
        return tool_error("mmx music generate requires at least one of: prompt, lyrics, instrumental, lyrics_optimizer.")

    out_path = args.get("output_path") or str(
        _default_music_dir() / f"mmx_{uuid.uuid4().hex[:8]}.mp3"
    )

    cmd = ["music", "generate", "--out", out_path, "--quiet"]
    if prompt:
        cmd.extend(["--prompt", prompt])
    if args.get("lyrics"):
        cmd.extend(["--lyrics", args["lyrics"]])
    if args.get("instrumental"):
        cmd.append("--instrumental")
    if args.get("lyrics_optimizer"):
        cmd.append("--lyrics-optimizer")

    # Optional style flags — only pass if user set them.
    optional_str_keys = [
        "vocals", "genre", "mood", "instruments", "tempo",
        "key", "avoid", "use_case", "structure", "references",
    ]
    for key in optional_str_keys:
        val = args.get(key)
        if val:
            cmd.extend([f"--{key.replace('_', '-')}", val])

    if args.get("bpm"):
        cmd.extend(["--bpm", str(args["bpm"])])

    try:
        result = run_mmx(cmd, timeout=300)
    except RuntimeError as exc:
        logger.warning("mmx music generate failed: %s", exc)
        return tool_error(str(exc))

    if result.returncode != 0:
        return tool_error(
            f"mmx music generate failed (exit {result.returncode}): "
            f"{(result.stderr or '').strip()}"
        )

    if not Path(out_path).exists():
        # mmx --quiet prints the saved path on stdout — check there.
        candidate = (result.stdout or "").strip().splitlines()[-1] if result.stdout.strip() else ""
        if candidate and Path(candidate).exists():
            out_path = candidate
        else:
            return tool_error(
                f"mmx music generate finished but no file at {out_path}. "
                f"stdout: {(result.stdout or '')[:200]!r}"
            )

    payload = {
        "success": True,
        "audio": str(Path(out_path).resolve()),
        "model": "music-3.0",
        "provider": "mmx",
        "prompt": prompt,
        "lyrics_provided": bool(args.get("lyrics")),
        "instrumental": bool(args.get("instrumental")),
    }
    return tool_result(payload)