"""hermes-mmx-backend — mmx (MiniMax CLI) backends for Hermes Agent.

Wraps the ``mmx`` CLI into four providers and two extra tools:

Providers (selection via ``config.yaml``):
    web.search_backend: "mmx"        → WebSearchProvider
    image_gen.provider: "mmx"        → ImageGenProvider
    video_gen.provider: "mmx"        → VideoGenProvider
    tts.provider:        "mmx"       → TTSProvider

Tools (always available when plugin enabled):
    mmx_music_generate               → text-to-music
    mmx_vision_describe              → image understanding

Requires ``mmx`` CLI installed and authenticated:
    uv tool install mmx-cli            # or: npm install -g mmx-cli
    mmx auth login                     # or: export MINIMAX_API_KEY=...

This plugin does NOT modify or override existing tools — it adds new
provider slots and tools so prompt caching stays intact. Users opt in
by setting ``provider: "mmx"`` in ``config.yaml`` (or just relying on
the new tools appearing).

Note on module layout: the providers live at the plugin root (not in a
sub-package). Putting them under ``providers/`` would collide with
hermes-agent's own ``providers/`` package on import; ``mmx_backends/``
worked when sub-modules were imported directly, but the plugin loader
imports only this ``__init__.py``, so a sub-package would never be on
``sys.path``. Flat layout matches the bundled ``plugins/spotify``
convention.
"""

from __future__ import annotations

from _mmx_runner import is_mmx_available, parse_mmx_json, run_mmx  # noqa: F401  (re-exported)
from image_gen import MMXImageGenProvider
from music_tool import MMX_MUSIC_GENERATE_SCHEMA, _handle_mmx_music_generate
from tts import MMXTTSProvider
from video_gen import MMXVideoGenProvider
from vision_tool import MMX_VISION_DESCRIBE_SCHEMA, _handle_mmx_vision_describe
from web_search import MMXWebSearchProvider


def register(ctx) -> None:
    """Register all mmx backends with the plugin context."""
    # Providers (selection via config.yaml)
    ctx.register_web_search_provider(MMXWebSearchProvider())
    ctx.register_image_gen_provider(MMXImageGenProvider())
    ctx.register_video_gen_provider(MMXVideoGenProvider())
    ctx.register_tts_provider(MMXTTSProvider())

    # Standalone tools (no ABC available for music / vision)
    ctx.register_tool(
        name="mmx_music_generate",
        toolset="mmx",
        schema=MMX_MUSIC_GENERATE_SCHEMA,
        handler=_handle_mmx_music_generate,
        emoji="🎶",
    )
    ctx.register_tool(
        name="mmx_vision_describe",
        toolset="mmx",
        schema=MMX_VISION_DESCRIBE_SCHEMA,
        handler=_handle_mmx_vision_describe,
        emoji="🔍",
    )