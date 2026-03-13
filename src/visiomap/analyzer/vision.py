"""Vision analyzer: OpenAI gpt-4o with deterministic mock fallback.

When VISIOMAP_OPENAI_API_KEY is set, photos are analyzed through the OpenAI
Vision API.  Otherwise a deterministic mock generates plausible results from
the URL hash — giving stable, reproducible output for development and testing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import httpx

from visiomap.config import settings

logger = logging.getLogger(__name__)

_ANALYSIS_PROMPT = """Analyze this photo for location intelligence. Return ONLY valid JSON:
{
  "crowd_density": <float 0-10, 0=empty 10=packed>,
  "crowd_count_estimate": <int rough headcount>,
  "age_groups": {"child": <pct>, "young_adult": <pct>, "adult": <pct>, "senior": <pct>},
  "mood": {"positive": <pct>, "neutral": <pct>, "negative": <pct>},
  "dominant_mood": "<positive|neutral|negative>",
  "environment_tags": ["<tag1>", "<tag2>", ...],
  "weather": "<sunny|cloudy|rainy|night|indoor|unknown>",
  "time_of_day": "<morning|afternoon|evening|night|unknown>"
}
Percentages in age_groups and mood must sum to 100. Be precise and analytical."""

_WEATHERS = ["sunny", "cloudy", "rainy", "night", "indoor", "sunny", "cloudy", "sunny"]
_TIMES = ["morning", "afternoon", "evening", "night", "afternoon", "morning", "afternoon", "evening"]
_MOODS = ["positive", "neutral", "negative"]
_ENV_TAGS = [
    ["outdoor", "busy", "commercial"],
    ["outdoor", "quiet", "residential"],
    ["indoor", "crowded", "mall"],
    ["outdoor", "park", "green"],
    ["indoor", "office", "modern"],
    ["outdoor", "market", "street"],
    ["indoor", "restaurant", "cozy"],
    ["outdoor", "beach", "tourist"],
]


class VisionAnalyzer:
    """Pluggable vision analyzer with OpenAI and mock backends."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def analyze(self, image_url: str) -> dict[str, Any]:
        if settings.use_real_analysis:
            return await self._analyze_openai(image_url)
        return self._analyze_mock(image_url)

    # ── OpenAI Vision ─────────────────────────────────────────────────────────

    async def _analyze_openai(self, image_url: str) -> dict[str, Any]:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=60.0)

        resp = await self._client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _ANALYSIS_PROMPT},
                            {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
                        ],
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]

        # Extract JSON from possible markdown fences
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        result["analysis_source"] = "openai"
        result["confidence"] = 0.85
        return result

    # ── Deterministic mock ────────────────────────────────────────────────────

    @staticmethod
    def _analyze_mock(image_url: str) -> dict[str, Any]:
        h = int(hashlib.sha256(image_url.encode()).hexdigest()[:8], 16)

        density = round(1.0 + (h % 80) / 10.0, 1)  # 1.0 — 9.0
        count = int(density * 5 + (h % 20))

        # Age distribution seeded by hash
        child = 5 + (h >> 8) % 15
        senior = 5 + (h >> 12) % 20
        young_adult = 20 + (h >> 16) % 25
        adult = 100 - child - senior - young_adult

        # Mood
        positive = 30 + (h >> 20) % 40
        negative = 5 + (h >> 24) % 20
        neutral = 100 - positive - negative

        mood_vals = {"positive": positive, "neutral": neutral, "negative": negative}
        dominant = max(mood_vals, key=mood_vals.get)  # type: ignore[arg-type]

        return {
            "crowd_density": density,
            "crowd_count_estimate": count,
            "age_groups": {
                "child": float(child),
                "young_adult": float(young_adult),
                "adult": float(adult),
                "senior": float(senior),
            },
            "mood": {
                "positive": float(positive),
                "neutral": float(neutral),
                "negative": float(negative),
            },
            "dominant_mood": dominant,
            "environment_tags": _ENV_TAGS[h % len(_ENV_TAGS)],
            "weather": _WEATHERS[h % len(_WEATHERS)],
            "time_of_day": _TIMES[h % len(_TIMES)],
            "confidence": round(0.60 + (h % 30) / 100, 2),
            "analysis_source": "mock",
        }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
