"""Orchestrates the four-agent sequential pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime

from models import GameState, GamePrompt
from agents.director import DirectorAgent
from agents.asset import AssetAgent
from agents.engineer import EngineerAgent
from agents.assembler import AssemblerAgent

# In-memory store for game states (prototype only)
games: dict[str, GameState] = {}


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
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        print(f"[Edit] Failed at editing: {exc}")

    games[game_id] = state
    return state
