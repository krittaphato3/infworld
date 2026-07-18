"""Architect Agent -- generates the game skeleton and scene structure."""

from __future__ import annotations

import re

from agents.base import BaseAgent
from client import llm_client
from models import GameState

_ARCHITECT_PROMPT = """\
You are a Phaser 3 game architect. Given the GDD, produce the COMPLETE game skeleton.

OUTPUT: A single JavaScript file with:
1. A BootScene class that generates ALL textures programmatically
2. Empty GameScene class with create/update stubs
3. The Phaser.Game config object
4. A SoundManager class for procedural audio

RULES:
- BootScene MUST generate textures using graphics.generateTexture() for ALL game objects
- Each texture should be visually distinct and appealing (not just colored rectangles)
- The Phaser config MUST include: scale: {{ mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }}
- The game MUST use parent: 'game-container'
- Output ONLY raw JavaScript, no markdown or code fences

GENRE: {genre}
GAME TITLE: {title}
CANVAS: {width}x{height}
COLOR PALETTE: {colors}
BACKGROUND COLOR: {bg_color}
DIFFICULTY CURVE: {difficulty_curve}
GAME FEEL NOTES: {game_feel_notes}
ASSETS NEEDED: {asset_list}

Generate the complete skeleton code now."""


class ArchitectAgent(BaseAgent):
    """Generates a game skeleton with boot scene, texture generation, and config."""

    name: str = "Architect"

    async def run(self, state: GameState) -> GameState:
        """Generate a game skeleton and store it in state.game_js."""
        if state.gdd is None:
            raise RuntimeError("No GDD available -- DirectorAgent must run first.")

        self.log("Generating game skeleton...")

        asset_list = self._format_assets(state)
        genre = getattr(state.gdd, "genre", "platformer")
        color_palette = getattr(state.gdd, "color_palette", ["#e94560", "#0f3460", "#00ff88"])
        difficulty_curve = getattr(state.gdd, "difficulty_curve", "gradual")
        game_feel_notes = getattr(state.gdd, "game_feel_notes", "")

        system_prompt = _ARCHITECT_PROMPT.format(
            genre=genre,
            title=state.gdd.title,
            width=state.gdd.canvas_width,
            height=state.gdd.canvas_height,
            colors=", ".join(color_palette),
            bg_color=state.gdd.background_color,
            difficulty_curve=difficulty_curve,
            game_feel_notes=game_feel_notes,
            asset_list=asset_list,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the game skeleton now."},
        ]

        raw_js = await llm_client.chat(messages, temperature=0.3, max_tokens=16384)
        clean_js = self._strip_code_fences(raw_js)

        if not clean_js or len(clean_js) < 100:
            raise RuntimeError("Architect produced empty or insufficient skeleton code")

        state.game_js = clean_js
        self.log(f"Skeleton generated ({len(clean_js)} chars)")
        return state

    @staticmethod
    def _format_assets(state: GameState) -> str:
        """Return a bullet list of assets with names, types, and URLs."""
        lines: list[str] = []
        for asset in state.assets:
            url = asset.asset_url or "(placeholder)"
            lines.append(f"- {asset.name} ({asset.type}): {url}")
        return "\n".join(lines) if lines else "(no assets)"

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove accidental markdown code fences from LLM output."""
        text = text.strip()
        pattern = r"^```(?:javascript|js)?\s*\n?(.*?)\n?\s*```$"
        match = re.match(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        pattern2 = r"^```(?:javascript|js)?\s*\n?(.*)"
        match2 = re.match(pattern2, text, re.DOTALL)
        if match2:
            return match2.group(1).strip()
        return text
