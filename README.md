# hermes-mmx-backend

[Hermes Agent](https://hermes-agent.nousresearch.com/) plugin that
backends **every model-facing capability** through the
[mmx-cli](https://github.com/MiniMax-AI/cli) (MiniMax CLI) — the same
underlying platform that powers the default Hermes model, but
addressable as a backend for web search, image / video / music
generation, TTS, and image-understanding.

## What you get

| Capability | How to enable |
|---|---|
| Web search | `web.search_backend: "mmx"` in `config.yaml` |
| Web extract | *(not provided — pair with [hermes-scrapling-backend](https://github.com/joyous-coder/hermes-scrapling-backend))* |
| Image generation | `image_gen.provider: "mmx"` in `config.yaml` |
| Video generation | `video_gen.provider: "mmx"` in `config.yaml` |
| Text-to-speech | `tts.provider: "mmx"` in `config.yaml` |
| Music generation | new tool `mmx_music_generate` (auto-registered) |
| Image understanding | new tool `mmx_vision_describe` (auto-registered) |

## Why a plugin instead of changing core tools?

Hermes ships with built-in providers for some of these (e.g. OpenAI for
images, Brave for web search). Our plugin **does not override** them — it
adds mmx as an *additional* provider slot, and you opt in by setting the
config key. This keeps prompt caching intact: turning mmx on or off
doesn't rebuild the system prompt.

## Prerequisites

```bash
# Install mmx-cli
uv tool install mmx-cli            # or: npm install -g mmx-cli

# Authenticate
mmx auth login                     # interactive OAuth
# or
export MINIMAX_API_KEY=sk-xxxxx    # env var fallback
```

The plugin shells out to `mmx` — no Python SDK is required at plugin
load time. mmx just needs to be in `PATH` and authenticated.

## Install

```bash
# From this repo (HTTPS)
hermes plugins install https://github.com/joyous-coder/hermes-mmx-backend.git

# Or shorthand
hermes plugins install joyous-coder/hermes-mmx-backend

# Pin to a specific commit for reproducibility
hermes plugins install joyous-coder/hermes-mmx-backend --ref <40-char-sha>
```

After install the new provider slots are visible in `hermes tools`
(Web Search / Image Generation / Video Generation / TTS picker rows),
and the new tools `mmx_music_generate` / `mmx_vision_describe` show up
in `hermes tools list`.

## Configure

In `~/.hermes/config.yaml`:

```yaml
web:
  search_backend: "mmx"            # route web_search through mmx search query
image_gen:
  provider: "mmx"                  # route image_generate through mmx image generate
video_gen:
  provider: "mmx"                  # route video_generate through mmx video generate
tts:
  provider: "mmx"                  # route text_to_speech through mmx speech synthesize
```

Music and vision come in as **standalone tools**; you don't configure
anything to use them, just call them.

## Tool signatures

### `mmx_music_generate`

```json
{
  "prompt":        "Upbeat folk about summer",   // style description
  "lyrics":        "[Verse]\nLa la la...",         // optional, mutually exclusive w/ instrumental
  "instrumental":  false,
  "vocals":        "warm female soprano",
  "genre":         "folk",
  "mood":          "warm",
  "instruments":   "acoustic guitar, piano",
  "tempo":         "moderate",
  "bpm":           95,
  "key":           "C major",
  "avoid":         "drums, distortion",
  "use_case":      "background music for video",
  "structure":     "verse-chorus-verse-bridge-chorus",
  "references":    "similar to Ed Sheeran",
  "lyrics_optimizer": false
}
```

### `mmx_vision_describe`

```json
{
  "image":  "C:/path/to/image.jpg",   // local path OR http(s) URL
  "prompt": "What is in this image?"  // default: "Describe the image."
}
```

## Limitations

- **`image_url` (image-to-image / editing) is not supported** by mmx's
  `image-01` model. The provider will return a clear
  `capability_not_supported` error if asked. Switch
  `image_gen.provider: "openai"` for that capability.
- **TTS model choice** — the built-in `minimax` provider and this `mmx`
  provider both call the same MiniMax API, but via different transport
  (HTTP vs `mmx speech synthesize` subprocess). Built-in always wins at
  dispatch time, so setting `tts.provider: "mmx"` only takes effect if
  no built-in `minimax` or `tts.providers.mmx` block is configured.

## Development

```bash
# Run tests
uv venv .testvenv --python 3.11
source .testvenv/Scripts/activate
uv pip install pytest
python -m pytest tests/ -v
```

The plugin's own code is hermes-agnostic except at the
`__init__.py::register(ctx)` boundary. Tests run against the real
hermes-agent ABCs (already in your environment) plus mocked subprocess
calls — no network calls, no API keys needed for CI.

## License

MIT — see [LICENSE](LICENSE).