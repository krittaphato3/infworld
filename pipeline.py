"""Orchestrates the four-agent sequential pipeline."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

from models import GameState, GamePrompt
from agents.director import DirectorAgent
from agents.asset import AssetAgent
from agents.engineer import EngineerAgent
from agents.assembler import AssemblerAgent
from config import settings

# In-memory store for game states (prototype only)
games: dict[str, GameState] = {}


def _save_meta(state: GameState) -> None:
    """Persist game metadata to disk so it survives server restarts."""
    meta = {
        "game_id": state.game_id,
        "prompt": state.prompt,
        "title": state.gdd.title if state.gdd else "Untitled",
        "status": state.status,
        "created_at": state.created_at,
        "asset_count": len(state.assets),
    }
    game_dir = os.path.join(settings.generated_dir, state.game_id)
    os.makedirs(game_dir, exist_ok=True)
    meta_path = os.path.join(game_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


async def run_pipeline(prompt: GamePrompt) -> GameState:
    """Run all four agents in sequence and return the final game state."""
    game_id = str(uuid.uuid4())[:8]
    state = GameState(game_id=game_id, prompt=prompt.prompt, status="running", created_at=datetime.now().isoformat())
    games[game_id] = state

    agents = [
        DirectorAgent(),
        AssetAgent(),
        EngineerAgent(),
        AssemblerAgent(),
    ]

    try:
        for agent in agents:
            state = await agent.run(state)
        state.status = "completed"
        _save_meta(state)
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        print(f"[Pipeline] Failed at {agent.name}: {exc}")

    games[game_id] = state
    return state


async def edit_game(game_id: str, edit_prompt: str) -> GameState:
    """Edit an existing game by re-running Engineer + Assembler agents."""
    if game_id not in games:
        raise ValueError(f"Game {game_id} not found")

    state = games[game_id]
    if state.status != "completed":
        raise ValueError(f"Game {game_id} is not completed (status: {state.status})")

    # Add the edit instruction to the prompt context
    original_prompt = state.prompt
    state.prompt = f"{original_prompt}\n\nEDIT INSTRUCTIONS: {edit_prompt}"
    state.status = "editing"
    games[game_id] = state

    try:
        # Re-run Engineer with the edit context
        engineer = EngineerAgent()
        state = await engineer.run(state)

        # Re-run Assembler
        assembler = AssemblerAgent()
        state = await assembler.run(state)

        state.status = "completed"
        _save_meta(state)
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        print(f"[Edit] Failed at editing: {exc}")

    games[game_id] = state
    return state
