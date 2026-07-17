"""Asset Agent -- generates images and audio for every asset in the GDD."""

from __future__ import annotations

import httpx

from agents.base import BaseAgent
from client import llm_client
from config import settings
from models import AssetRequirement, GameState

_PLACEHOLDER_AUDIO_URLS: dict[str, str] = {
    "audio_sfx": "https://actions.google.com/sounds/v1/alarms/beep_short.ogg",
    "audio_music": "https://actions.google.com/sounds/v1/alarms/beep_short.ogg",
}


class AssetAgent(BaseAgent):
    """Generates or fetches URLs for all assets declared in the GDD."""

    name: str = "Asset"

    async def run(self, state: GameState) -> GameState:
        """Iterate over assets, generate each one, and store its URL."""
        if not state.assets:
            self.log("No assets to generate.")
            return state

        total = len(state.assets)
        for idx, asset in enumerate(state.assets, start=1):
            self.log(f"[{idx}/{total}] Generating {asset.type}: {asset.name}")
            try:
                if asset.type == "image":
                    asset.asset_url = await self._generate_image(asset)
                elif asset.type.startswith("audio"):
                    asset.asset_url = await self._generate_audio(asset)
                else:
                    self.log(f"Unknown asset type '{asset.type}', skipping.")
            except Exception as exc:
                self.log(f"Failed to generate {asset.name}: {exc}")
                asset.asset_url = ""

        self.log("Asset generation complete.")
        return state

    # ── Private helpers ───────────────────────────────────────────────

    async def _generate_image(self, asset: AssetRequirement) -> str:
        """Call the image generation API and return the URL."""
        if not settings.image_api_key or settings.image_api_key.startswith("sk-your"):
            self.log(f"Image API not configured, using placeholder for {asset.name}")
            return self._placeholder_image(asset.name)
        return await llm_client.generate_image(asset.description)

    @staticmethod
    def _placeholder_image(name: str) -> str:
        """Return a data URI SVG placeholder for missing images."""
        import base64

        colors = ["#e94560", "#0f3460", "#00ff88", "#ff6b81", "#8888aa"]
        color = colors[hash(name) % len(colors)]
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">'
            f'<rect width="128" height="128" fill="{color}"/>'
            f'<text x="64" y="64" text-anchor="middle" dominant-baseline="middle" '
            f'fill="white" font-size="10" font-family="monospace">{name}</text>'
            f'</svg>'
        )
        return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"

    async def _generate_audio(self, asset: AssetRequirement) -> str:
        """Attempt to generate audio via the configured API; fall back to a placeholder."""
        if settings.audio_api_key and not settings.audio_api_key.startswith("sk-your"):
            try:
                return await self._call_audio_api(asset)
            except Exception as exc:
                self.log(f"Audio API call failed, using placeholder: {exc}")

        placeholder = _PLACEHOLDER_AUDIO_URLS.get(asset.type, _PLACEHOLDER_AUDIO_URLS["audio_sfx"])
        self.log(f"Using placeholder audio for {asset.name}")
        return placeholder

    async def _call_audio_api(self, asset: AssetRequirement) -> str:
        """POST to the audio generation endpoint and return the audio URL or base64."""
        url = f"{settings.audio_api_url}/audio/speech"
        headers = {
            "Authorization": f"Bearer {settings.audio_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.audio_model,
            "input": asset.description,
            "voice": "alloy",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "json" in content_type:
                data = resp.json()
                return data.get("url", data.get("audio_url", ""))
            b64 = resp.content
            import base64
            encoded = base64.b64encode(b64).decode()
            return f"data:audio/mpeg;base64,{encoded}"
