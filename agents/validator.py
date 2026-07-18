"""Validator Agent -- reviews generated game code for errors and fixes them."""

from __future__ import annotations

import re

from agents.base import BaseAgent
from client import llm_client
from models import GameState

_VALIDATOR_PROMPT = """\
You are a Phaser 3 game code reviewer. Review the following game code for errors.

CHECK FOR:
1. Is there a BootScene that generates all textures?
2. Are all texture keys used in create() generated in preload()?
3. Is the Phaser config correct (parent: 'game-container', scale settings)?
4. Are there any obvious JavaScript syntax errors?
5. Does the game have win/loss conditions?
6. Does the game have player input handling?
7. Is there a score/lives system?
8. Will this code run in a browser without errors?

If there are errors, output the COMPLETE fixed game code.
If the code is correct, output it unchanged.

GAME CODE:
```javascript
{game_js}
```

Output the complete game code (fixed if needed)."""


class ValidatorAgent(BaseAgent):
    """Reviews generated Phaser 3 code for common errors and fixes them."""

    name: str = "Validator"

    async def run(self, state: GameState) -> GameState:
        """Validate and optionally fix the game JS code."""
        if not state.game_js:
            raise RuntimeError("No game JS to validate -- EngineerAgent must run first.")

        self.log("Validating game code...")

        # Basic structural checks before sending to LLM
        issues = self._quick_check(state.game_js)
        if issues:
            self.log(f"Quick check found {len(issues)} issue(s): {'; '.join(issues)}")

        system_prompt = _VALIDATOR_PROMPT.format(game_js=state.game_js)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Review and fix the code if needed. Output the complete code."},
        ]

        raw_js = await llm_client.chat(messages, temperature=0.2, max_tokens=16384)
        clean_js = self._strip_code_fences(raw_js)

        if not clean_js or len(clean_js) < 100:
            self.log("Validator returned insufficient code, keeping original")
            return state

        state.game_js = clean_js
        self.log(f"Validation complete ({len(clean_js)} chars)")
        return state

    @staticmethod
    def _quick_check(js_code: str) -> list[str]:
        """Run fast structural checks on the JS code before LLM validation."""
        issues: list[str] = []
        if "parent:" not in js_code and "parent :" not in js_code:
            issues.append("Missing Phaser parent config")
        if "generateTexture" not in js_code and "this.make.graphics" not in js_code:
            issues.append("No texture generation found")
        if "new Phaser.Game" not in js_code:
            issues.append("Missing Phaser.Game instantiation")
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
        if depth > 0:
            issues.append(f"Unbalanced braces (depth={depth})")
        return issues

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
