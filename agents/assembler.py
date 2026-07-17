"""Assembler Agent -- bundles game JS into a complete HTML file and writes to disk."""

from __future__ import annotations

import html as html_mod
import os
from pathlib import Path

from agents.base import BaseAgent
from config import settings
from models import GameState

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ 
      background: #1a1a2e; 
      display: flex; 
      justify-content: center; 
      align-items: center; 
      min-height: 100vh;
      font-family: 'Segoe UI', sans-serif;
    }}
    #game-container {{
      border: 2px solid #e94560;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 0 30px rgba(233,69,96,0.3);
    }}
  </style>
</head>
<body>
  <div id="game-container"></div>
  <script src="https://cdn.jsdelivr.net/npm/phaser@3.80.1/dist/phaser.min.js"></script>
  <script>
{game_js}
  </script>
</body>
</html>"""


class AssemblerAgent(BaseAgent):
    """Writes the final HTML file to the generated output directory."""

    name: str = "Assembler"

    async def run(self, state: GameState) -> GameState:
        """Render the HTML template and persist it to generated/{game_id}/index.html."""
        if not state.game_js:
            raise RuntimeError("No game JS available -- EngineerAgent must run first.")

        title = state.gdd.title if state.gdd else "Infinite Realms Game"

        safe_title = html_mod.escape(title)
        clean_js = self._strip_code_fences(state.game_js)
        safe_js = clean_js.replace("</script>", "<\\/script>")
        html = _HTML_TEMPLATE.format(title=safe_title, game_js=safe_js)

        game_dir = os.path.join(settings.generated_dir, state.game_id)
        os.makedirs(game_dir, exist_ok=True)

        html_path = os.path.join(game_dir, "index.html")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html)

        state.index_html = html
        state.status = "completed"
        self.log(f"HTML written to {html_path}")
        return state

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown code fences from LLM output as a safety net."""
        import re
        pattern = r"^```(?:javascript|js)?\s*\n?(.*?)\n?\s*```$"
        match = re.match(pattern, text.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
