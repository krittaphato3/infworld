"""Engineer Agent -- generates a complete Phaser.js game from the GDD and asset URLs."""

from __future__ import annotations

from agents.base import BaseAgent
from client import llm_client
from models import GameState


_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert Phaser.js game developer. Generate a COMPLETE, working Phaser 3 game as a single JavaScript file.

CRITICAL RULES:
- Output ONLY raw JavaScript code. No markdown, no code fences, no explanations.
- The code will be injected into an HTML file that already loads Phaser from CDN.
- Use the variable name `config` for the Phaser.Game configuration object.
- All assets must use the EXACT URLs provided below.
- The game must be immediately playable when loaded.
- Include proper preload(), create(), and update() methods.
- Handle all win/loss conditions from the GDD.
- The game canvas size must be {canvas_width}x{canvas_height}.
- The background color must be {background_color}.

ASSET URLS:
{asset_list}

GAME DESIGN DOCUMENT:
{gdd_json}

Output only the JavaScript code, nothing else."""


class EngineerAgent(BaseAgent):
    """Generates a self-contained Phaser 3 game script from the GDD."""

    name: str = "Engineer"

    async def run(self, state: GameState) -> GameState:
        """Build the system prompt and ask the LLM for complete game JS."""
        if state.gdd is None:
            raise RuntimeError("No GDD available -- DirectorAgent must run first.")

        self.log("Generating Phaser.js game code...")

        asset_list = self._format_asset_list(state)
        gdd_json = state.gdd.model_dump_json(indent=2)

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            canvas_width=state.gdd.canvas_width,
            canvas_height=state.gdd.canvas_height,
            background_color=state.gdd.background_color,
            asset_list=asset_list,
            gdd_json=gdd_json,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the complete game code now."},
        ]

        raw_js = await llm_client.chat(messages, temperature=0.5)
        clean_js = self._strip_code_fences(raw_js)

        state.game_js = clean_js
        self.log(f"Game JS generated ({len(clean_js)} chars)")
        return state

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _format_asset_list(state: GameState) -> str:
        """Return a numbered list of assets with names, types, and URLs."""
        lines: list[str] = []
        for i, asset in enumerate(state.assets, start=1):
            url = asset.asset_url or "(not yet generated)"
            note = " [placeholder]" if "data:image/svg+xml" in url or "google.com/sounds" in url else ""
            lines.append(f"{i}. {asset.name} ({asset.type}): {url}{note}")
        return "\n".join(lines) if lines else "(no assets)"

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove accidental markdown code fences from LLM output."""
        import re

        pattern = r"^```(?:javascript|js)?\s*\n?(.*?)\n?\s*```$"
        match = re.match(pattern, text.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
