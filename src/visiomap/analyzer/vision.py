"""
Pluggable vision analysis module.
Uses OpenAI Vision API (gpt-4o) if OPENAI_API_KEY is set,
otherwise deterministic mock based on URL hash (dev/testing).
"""
import hashlib
import json
import random
from typing import Optional

import httpx

from visiomap.config import settings
from visiomap.schemas.media import AnalysisResult

_ENV_POOL = [
    "outdoor", "indoor", "busy", "quiet", "commercial", "residential",
    "daylight", "evening", "crowded", "spacious", "clean", "market",
    "transit", "park", "restaurant", "retail", "street", "plaza",
]

_WEATHER_OPTS = ["sunny", "overcast", "rainy", "cloudy", "indoor"]
_TIME_OPTS = ["morning", "afternoon", "evening", "night"]


def _mock(url: str) -> AnalysisResult:
    """Deterministic mock — same URL always returns same result."""
    rng = random.Random(int(hashlib.md5(url.encode()).hexdigest(), 16))

    density = round(rng.uniform(0.8, 9.4), 1)
    count = int(density * rng.uniform(6, 22))

    c, y, a, s = rng.randint(5, 18), rng.randint(20, 38), rng.randint(28, 44), 0
    s = max(5, 100 - c - y - a)
    total = c + y + a + s
    age = {
        "child": round(c / total * 100),
        "young_adult": round(y / total * 100),
        "adult": round(a / total * 100),
        "senior": round(s / total * 100),
    }

    pos, neu = rng.randint(30, 68), rng.randint(12, 35)
    neg = max(0, 100 - pos - neu)
    mood = {"positive": pos, "neutral": neu, "negative": neg}
    dominant = max(mood, key=mood.get)

    pool = _ENV_POOL.copy()
    rng.shuffle(pool)
    env_tags = sorted(pool[: rng.randint(3, 6)])

    return AnalysisResult(
        crowd_density=density,
        crowd_count_estimate=count,
        age_groups=age,
        mood=mood,
        dominant_mood=dominant,
        environment_tags=env_tags,
        weather=rng.choice(_WEATHER_OPTS),
        time_of_day=rng.choice(_TIME_OPTS),
        confidence=round(rng.uniform(0.60, 0.93), 2),
        analysis_source="mock",
    )


_VISION_PROMPT = (
    "Analyze this image for location intelligence. "
    "Respond ONLY with valid JSON (no markdown) containing:\n"
    "crowd_density (float 0-10), crowd_count_estimate (int), "
    "age_groups (object: child/young_adult/adult/senior as % summing 100), "
    "mood (object: positive/neutral/negative as % summing 100), "
    "dominant_mood (string), environment_tags (array of 3-6 strings), "
    "weather (sunny|overcast|rainy|cloudy|indoor), "
    "time_of_day (morning|afternoon|evening|night), "
    "confidence (float 0-1)."
)


async def _call_openai(image_url: str, api_key: str) -> AnalysisResult:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o",
                "max_tokens": 600,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }],
            },
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        data["analysis_source"] = "openai"
        return AnalysisResult(**data)


async def analyze(image_url: str) -> AnalysisResult:
    """
    Analyze an image. Uses OpenAI Vision if OPENAI_API_KEY configured,
    falls back to deterministic mock otherwise.
    """
    if settings.openai_api_key:
        try:
            return await _call_openai(image_url, settings.openai_api_key)
        except Exception as exc:
            result = _mock(image_url)
            return result.model_copy(update={
                "analysis_source": "mock_fallback",
            })
    return _mock(image_url)
