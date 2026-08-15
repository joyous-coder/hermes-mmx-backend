"""mmx WebSearchProvider — replaces built-in web_search via mmx search query.

Wraps ``mmx search query --q <query>`` which returns up to 5 organic
results with title/link/snippet/date. Maps to the standard WebSearchProvider
response shape so config-level ``web.search_backend: "mmx"`` is a drop-in.

Notes:
- The mmx search backend is a MiniMax-internal web index — quality may
  differ from Brave/Tavily/Exa. For users who primarily need *something*
  to surface URLs (and then extract via scrapling for example), this is
  a zero-credential option once mmx auth is set up.
- Search-only. Use a separate extract backend (``scrapling`` for
  example) for ``web_extract``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from agent.web_search_provider import WebSearchProvider

from _mmx_runner import is_mmx_available, parse_mmx_json, run_mmx

logger = logging.getLogger(__name__)


class MMXWebSearchProvider(WebSearchProvider):
    """mmx-cli search backend — text query → organic results."""

    @property
    def name(self) -> str:
        return "mmx"

    @property
    def display_name(self) -> str:
        return "MiniMax (mmx-cli)"

    def is_available(self) -> bool:
        return is_mmx_available()

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        # Extraction lives in a separate provider (e.g. scrapling).
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Run ``mmx search query`` and map to the standard envelope.

        mmx ``search query`` ignores ``--limit``; it returns up to 5 organic
        results by default. We slice to ``limit`` after the fact.
        """
        try:
            result = run_mmx(
                ["search", "query", "--q", query, "--output", "json", "--quiet"],
                timeout=30,
            )
        except RuntimeError as exc:
            logger.warning("mmx web_search invocation failed: %s", exc)
            return {"success": False, "error": str(exc)}

        try:
            data = parse_mmx_json(result)
        except RuntimeError as exc:
            logger.warning("mmx web_search parse failed: %s", exc)
            return {"success": False, "error": str(exc)}

        # mmx shape:
        #   {"organic": [{"title","link","snippet","date",...}, ...],
        #    "base_resp": {"status_code": 0, ...}}
        organic = data.get("organic") or []
        if not organic:
            logger.info("mmx web_search '%s' returned 0 results", query)
            return {"success": True, "data": {"web": []}}

        web_results = []
        for i, item in enumerate(organic[: max(1, limit)]):
            web_results.append(
                {
                    "title": str(item.get("title", "")),
                    "url": str(item.get("link", "")),
                    "description": str(item.get("snippet", "")),
                    "position": i + 1,
                }
            )

        logger.info(
            "mmx web_search '%s': %d results (limit %d)", query, len(web_results), limit
        )
        return {"success": True, "data": {"web": web_results}}

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "MiniMax (mmx-cli)",
            "badge": "bundled",
            "tag": "Uses MiniMax web index via mmx-cli. Free with mmx auth.",
            "env_vars": [],
        }