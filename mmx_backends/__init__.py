"""Provider implementations for mmx backends.

We deliberately do NOT eagerly ``from . import image_gen, …`` here:
each provider module imports ``agent.web_search_provider`` /
``agent.tts_provider`` etc. at module top level. If those modules
aren't available (e.g. when running plugin unit tests outside the
full hermes-agent install), eager import breaks the whole package
import path. Hermes itself never imports this ``__init__`` directly —
the plugin entry point is the top-level ``register(ctx)`` in
``D:/Links/Tools/hermes-mmx-backend/__init__.py``, which imports
each provider explicitly.
"""

# Marker so ``import providers`` works without side effects.
__all__: list[str] = []