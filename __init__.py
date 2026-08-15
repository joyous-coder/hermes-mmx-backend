"""hermes-mmx-backend — mmx (MiniMax CLI) backends for Hermes Agent.

Wraps the ``mmx`` CLI into four providers and two extra tools.

Plugin layout: providers live at the plugin root. The Hermes plugin
loader imports this ``__init__.py`` as a flat module — we use
``spec_from_file_location`` to load each sibling by absolute path so
that the import doesn't depend on ``sys.path``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent


def _load(name: str):
    """Load a sibling module file by absolute path."""
    path = _PLUGIN_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load sibling module {name}")
    module = importlib.util.module_from_spec(spec)
    # Cache under both bare name AND our package name so Python's import
    # system can find it via either path.
    sys.modules.setdefault(name, module)
    full_name = f"{__name__}.{name}"
    sys.modules.setdefault(full_name, module)
    spec.loader.exec_module(module)
    return module


# Load sibling modules. The runner must come first (used by the others).
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
    ctx.register_web_search_provider(MMXWebSearchProvider())
    ctx.register_image_gen_provider(MMXImageGenProvider())
    ctx.register_video_gen_provider(MMXVideoGenProvider())
    ctx.register_tts_provider(MMXTTSProvider())

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