"""Engineer Agent -- generates a complete Phaser.js game from the GDD and asset URLs."""

from __future__ import annotations

from agents.base import BaseAgent
from client import llm_client
from models import GameState


_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert Phaser 3 game developer. Generate a COMPLETE, working Phaser 3 game.

## OUTPUT RULES
- Output ONLY raw JavaScript. No markdown, no code fences, no explanations.
- The code will be injected into HTML that already loads Phaser 3.80 from CDN.
- The game must be immediately playable with zero errors.

## CODE STRUCTURE (MUST FOLLOW)
```
// 1. Variable declarations at top
var player, platforms, score, scoreText, cursors, gameOver;

// 2. Function definitions
function preload() {{ /* create textures here */ }}
function create() {{ /* setup game objects */ }}
function update() {{ /* game loop */ }}

// 3. Config object (AFTER all functions)
var config = {{
    type: Phaser.AUTO,
    width: {canvas_width},
    height: {canvas_height},
    backgroundColor: '{background_color}',
    parent: 'game-container',
    physics: {{
        default: 'arcade',
        arcade: {{ gravity: {{ y: 800 }}, debug: false }}
    }},
    scene: {{ preload: preload, create: create, update: update }}
}};

// 4. Game instance (LAST line)
var game = new Phaser.Game(config);
```

## SELF-SUFFICIENT GRAPHICS (CRITICAL)
When assets show "[placeholder]" or "CREATE IN CODE", you MUST create all graphics in code using Phaser's graphics API.
NEVER use this.load.image() for placeholder assets. Instead, in preload():

```javascript
function preload() {{
    // Create player texture (colored rectangle with eyes)
    var g = this.make.graphics({{ add: false }});
    g.fillStyle(0x00aaff, 1);
    g.fillRect(0, 0, 32, 48);
    g.fillStyle(0xffffff, 1);
    g.fillCircle(10, 12, 4);
    g.fillCircle(22, 12, 4);
    g.fillStyle(0x000000, 1);
    g.fillCircle(10, 12, 2);
    g.fillCircle(22, 12, 2);
    g.generateTexture('player', 32, 48);
    g.destroy();

    // Create platform texture
    var g2 = this.make.graphics({{ add: false }});
    g2.fillStyle(0x44aa44, 1);
    g2.fillRect(0, 0, 200, 32);
    g2.fillStyle(0x66cc66, 1);
    g2.fillRect(0, 0, 200, 8);
    g2.generateTexture('platform', 200, 32);
    g2.destroy();

    // Create coin texture
    var g3 = this.make.graphics({{ add: false }});
    g3.fillStyle(0xffdd00, 1);
    g3.fillCircle(12, 12, 12);
    g3.fillStyle(0xffaa00, 1);
    g3.fillCircle(12, 12, 8);
    g3.generateTexture('coin', 24, 24);
    g3.destroy();

    // Create enemy texture
    var g4 = this.make.graphics({{ add: false }});
    g4.fillStyle(0xff4444, 1);
    g4.fillRect(0, 0, 32, 32);
    g4.fillStyle(0xffffff, 1);
    g4.fillCircle(10, 10, 4);
    g4.fillCircle(22, 10, 4);
    g4.generateTexture('enemy', 32, 32);
    g4.destroy();

    // Create particle texture
    var g5 = this.make.graphics({{ add: false }});
    g5.fillStyle(0xffffff, 1);
    g5.fillCircle(4, 4, 4);
    g5.generateTexture('particle', 8, 8);
    g5.destroy();
}}
```

Make graphics DETAILED and VISUALLY APPEALING:
- Player: colored body with eyes and features
- Enemies: menacing shapes with eyes
- Platforms: textured with grass/stone patterns
- Coins: shiny gold with highlights
- Backgrounds: gradient sky, stars, clouds using graphics
- Particles: for effects (explosion, trail, spark)

## AUDIO (WHEN PLACEHOLDERS)
When audio shows "[placeholder]" or "CREATE IN CODE", use the Web Audio API for simple sounds:

```javascript
function playSound(frequency, duration, type) {{
    try {{
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = frequency;
        osc.type = type || 'square';
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + duration);
    }} catch(e) {{}}
}}
```

Use for: jump sounds (440Hz, 0.1s), collect sounds (880Hz, 0.15s), death sounds (220Hz, 0.3s), shoot sounds (660Hz, 0.05s).

## GAME QUALITY REQUIREMENTS
- Smooth player movement with acceleration/deceleration
- Camera follow for scrolling games
- Visual feedback (score display, particle effects on collect/hit)
- Screen shake on impacts
- Proper game states (playing, game over, win) with restart
- Responsive controls (variable jump height based on hold time)
- Enemy AI (patrol, chase, or spawn patterns)
- At least 3-5 distinct visual elements (not all same colored rectangles)

## ASSET URLS
{asset_list}

## GAME DESIGN DOCUMENT
{gdd_json}

{edit_section}

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

        # Build edit section for iterative editing or skeleton enhancement
        edit_section = ""

        has_skeleton = state.game_js and len(state.game_js) > 500
        is_edit_mode = "EDIT INSTRUCTIONS:" in state.prompt

        if has_skeleton and not is_edit_mode:
            # Architect provided a skeleton -- enhance it with full game logic
            edit_section = f"""
## EXISTING GAME SKELETON
The game skeleton has been generated by the Architect. Enhance it with full game logic.
Keep the BootScene and texture generation. Fill in the GameScene with complete mechanics.

```javascript
{state.game_js}
```

Apply the EDIT INSTRUCTIONS below while keeping the skeleton structure intact.
"""
        elif is_edit_mode:
            edit_section = f"""
## EXISTING GAME CODE (modify this, don't rewrite from scratch)
The current game code is below. Apply the edit instructions while keeping everything else working:

```javascript
{state.game_js}
```

## EDIT INSTRUCTIONS
{state.prompt.split("EDIT INSTRUCTIONS:")[-1].strip()}

IMPORTANT: Output the COMPLETE modified game code, not just the changes. The entire game must work as a single file.
"""

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            canvas_width=state.gdd.canvas_width,
            canvas_height=state.gdd.canvas_height,
            background_color=state.gdd.background_color,
            asset_list=asset_list,
            gdd_json=gdd_json,
            edit_section=edit_section,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the complete game code now."},
        ]

        raw_js = await llm_client.chat(messages, temperature=0.5, max_tokens=16384)
        clean_js = self._strip_code_fences(raw_js)

        # If output looks truncated (no closing brace at top level), retry once
        if clean_js and not self._is_complete(clean_js):
            self.log("Output appears truncated, retrying with higher token limit...")
            raw_js = await llm_client.chat(messages, temperature=0.3, max_tokens=16384)
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
            if "PLACEHOLDER:code-drawn" in url:
                note = " [CREATE IN CODE - draw this sprite in preload()]"
            elif "PLACEHOLDER:code-sound" in url:
                note = " [CREATE IN CODE - use Web Audio API oscillator]"
            elif "google.com/sounds" in url:
                note = " [placeholder audio]"
            else:
                note = ""
            lines.append(f"{i}. {asset.name} ({asset.type}): {url}{note}")
        return "\n".join(lines) if lines else "(no assets)"

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove accidental markdown code fences from LLM output."""
        import re

        text = text.strip()
        # Try full match: opening fence + content + closing fence
        pattern = r"^```(?:javascript|js)?\s*\n?(.*?)\n?\s*```$"
        match = re.match(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Try partial match: opening fence but no closing (truncated output)
        pattern2 = r"^```(?:javascript|js)?\s*\n?(.*)"
        match2 = re.match(pattern2, text, re.DOTALL)
        if match2:
            return match2.group(1).strip()
        return text

    @staticmethod
    def _is_complete(js_code: str) -> bool:
        """Heuristic: check if the JS has balanced braces at the top level."""
        depth = 0
        in_string = False
        string_char = None
        for ch in js_code:
            if in_string:
                if ch == string_char:
                    in_string = False
                continue
            if ch in ('"', "'", '`'):
                in_string = True
                string_char = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        return depth <= 0
