"""Director Agent -- generates a GameDesignDocument from a user prompt."""

from __future__ import annotations

import json

from agents.base import BaseAgent
from client import llm_client
from models import GameDesignDocument, GameState


_SYSTEM_PROMPT = """\
You are a game design document generator. Given a user's game premise, output ONLY a valid JSON object matching this exact schema (no markdown, no code fences, just raw JSON):
{
  "title": "Game Title",
  "premise": "One paragraph description",
  "genre": "platformer",
  "mechanics": ["mechanic1", "mechanic2", ...],
  "controls": "Description of player controls",
  "win_condition": "How the player wins",
  "loss_condition": "How the player loses",
  "canvas_width": 800,
  "canvas_height": 600,
  "background_color": "#2d2d2d",
  "color_palette": ["#e94560", "#0f3460", "#00ff88"],
  "difficulty_curve": "gradual",
  "game_feel_notes": "Specific juice instructions for game feel",
  "assets": [
    {
      "name": "asset_identifier_snake_case",
      "type": "image",
      "description": "Detailed prompt for image generation"
    },
    {
      "name": "sfx_identifier",
      "type": "audio_sfx",
      "description": "Description of sound effect"
    },
    {
      "name": "music_identifier",
      "type": "audio_music",
      "description": "Description of background music"
    }
  ]
}
Rules:
- genre must be one of: platformer, shooter, puzzle, idle, rpg, adventure
- color_palette: 3-5 hex colors that define the game's visual identity
- difficulty_curve: one of "gradual", "spike", "constant", "wave", or "steep"
- game_feel_notes: specific instructions for juice/polish (e.g. "screen shake on hits", "particle trails", "bouncy UI elements")
- Generate 3-6 image assets minimum (player sprite, enemies, backgrounds, UI elements)
- Generate at least 1 audio_sfx and 1 audio_music
- Keep mechanics simple but fun — this is a browser game
- All asset descriptions should be detailed enough for AI image/audio generation
- Output ONLY the JSON object, nothing else"""


class DirectorAgent(BaseAgent):
    """Produces a structured GameDesignDocument from a free-text game prompt."""

    name: str = "Director"

    async def run(self, state: GameState) -> GameState:
        """Generate a GDD and populate state.gdd / state.assets."""
        self.log(f"Generating GDD for prompt: {state.prompt[:80]}...")

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": state.prompt},
        ]

        gdd_data = await llm_client.chat_json(messages)
        gdd = GameDesignDocument(**gdd_data)

        state.gdd = gdd
        state.assets = list(gdd.assets)
        self.log(f"GDD generated: '{gdd.title}' with {len(gdd.assets)} assets")
        return state
