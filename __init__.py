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

Plugin layout note: the Hermes plugin loader imports ``__init__.py`` as
a single-file module via ``spec_from_file_location`` — it does NOT add
the plugin directory to ``sys.path``, so we cannot import sibling files
by their bare names. We use ``spec_from_file_location`` ourselves to
load the sibling modules explicitly. (Sub-package layouts like
``providers/`` collide with hermes-agent's own ``providers/`` package,
and the relative-import path ``from ._mmx_runner import …`` fails
because the loader's spec doesn't expose ``__path__`` correctly for
this use case.)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent


def _load(name: str):
    """Load a sibling module file by name.

    Uses ``spec_from_file_location`` so we don't depend on ``sys.path``
    or ``__path__`` being set correctly by the plugin loader. Returns
    the loaded module.
    """
    spec = importlib.util.spec_from_file_location(
        name, _PLUGIN_DIR / f"{name}.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load sibling module {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{__name__}.{name}"] = module  # cache under our name
    spec.loader.exec_module(module)
    return module


# Load all sibling modules up front. Order matters only for ``_mmx_runner``
# which the providers import.
_mmx_runner = _load("_mmx_runner")
_image_gen_mod = _load("image_gen")
_video_gen_mod = _load("video_gen")
_tts_mod = _load("tts")
_web_search_mod = _load("web_search")
_music_tool_mod = _load("music_tool")
_vision_tool_mod = _load("vision_tool")

MMXImageGenProvider = _image_gen_mod.MMXImageGenProvider
MMXVideoGenProvider = _video_gen_mod.MMXVideoGenProvider
MMXTTSProvider = _tts_mod.MMXTTSProvider
MMXWebSearchProvider = _web_search_mod.MMXWebSearchProvider
MMX_MUSIC_GENERATE_SCHEMA = _music_tool_mod.MMX_MUSIC_GENERATE_SCHEMA
_handle_mmx_music_generate = _music_tool_mod._handle_mmx_music_generate
MMX_VISION_DESCRIBE_SCHEMA = _vision_tool_mod.MMX_VISION_DESCRIBE_SCHEMA
_handle_mmx_vision_describe = _vision_tool_mod._handle_mmx_vision_describe


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