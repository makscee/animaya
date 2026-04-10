"""Image generation via Google Gemini API.

Usage: python -m bot.features.image_gen "a cat in space" /data/uploads/output.png
"""
from __future__ import annotations

import base64
import os
import sys

import httpx

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent"


def generate(prompt: str, output_path: str) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_API_KEY not set"

    resp = httpx.post(
        GEMINI_URL,
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        },
        timeout=60,
    )

    if resp.status_code != 200:
        return f"Error: Gemini API returned {resp.status_code}: {resp.text[:200]}"

    data = resp.json()
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline_data = part.get("inlineData")
            if inline_data and inline_data.get("data"):
                image_bytes = base64.b64decode(inline_data["data"])
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                return f"Image saved to {output_path} ({len(image_bytes)} bytes)"

    return "Error: No image in response"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m bot.features.image_gen <prompt> <output_path>")
        sys.exit(1)
    print(generate(sys.argv[1], sys.argv[2]))
