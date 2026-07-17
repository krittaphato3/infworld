"""Orchestrates the four-agent sequential pipeline."""

from __future__ import annotations

import uuid

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
    state = GameState(game_id=game_id, prompt=prompt.prompt, status="running")
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
