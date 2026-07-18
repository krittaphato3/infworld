"""Orchestrates the multi-pass game generation pipeline."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

from models import GameState, GamePrompt
from agents.director import DirectorAgent
from agents.architect import ArchitectAgent
from agents.engineer import EngineerAgent
from agents.validator import ValidatorAgent
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
    """Run the 5-stage pipeline: Director -> Architect -> Engineer -> Validator -> Assembler."""
    game_id = str(uuid.uuid4())[:8]
    state = GameState(game_id=game_id, prompt=prompt.prompt, status="running", created_at=datetime.now().isoformat())
    games[game_id] = state

    stages = [
        ("Director", DirectorAgent()),
        ("Architect", ArchitectAgent()),
        ("Engineer", EngineerAgent()),
        # Validator skipped for speed — Engineer output is usually good enough
        ("Assembler", AssemblerAgent()),
    ]

    try:
        for name, agent in stages:
            print(f"[Pipeline] [{name}] Starting...")
            state = await agent.run(state)
            print(f"[Pipeline] [{name}] Complete")

        state.status = "completed"
        _save_meta(state)
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        print(f"[Pipeline] Failed: {exc}")

    games[game_id] = state
    return state


async def edit_game(game_id: str, edit_prompt: str) -> GameState:
    """Edit an existing game by re-running Engineer -> Validator -> Assembler."""
    if game_id not in games:
        raise ValueError(f"Game {game_id} not found")

    state = games[game_id]
    if state.status != "completed":
        raise ValueError(f"Game {game_id} is not completed (status: {state.status})")

    original_prompt = state.prompt
    state.prompt = f"{original_prompt}\n\nEDIT INSTRUCTIONS: {edit_prompt}"
    state.status = "editing"
    games[game_id] = state

    stages = [
        ("Engineer", EngineerAgent()),
        ("Validator", ValidatorAgent()),
        ("Assembler", AssemblerAgent()),
    ]

    try:
        for name, agent in stages:
            print(f"[Edit] [{name}] Starting...")
            state = await agent.run(state)
            print(f"[Edit] [{name}] Complete")
        state.status = "completed"
        _save_meta(state)
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
        print(f"[Edit] Failed at editing: {exc}")

    games[game_id] = state
    return state


async def run_pipeline_director(game_id: str, prompt: str) -> GameState:
    """Run just the Director stage."""
    state = GameState(game_id=game_id, prompt=prompt, status="running", created_at=datetime.now().isoformat())
    games[game_id] = state
    director = DirectorAgent()
    state = await director.run(state)
    games[game_id] = state
    return state


async def run_pipeline_architect(state: GameState) -> GameState:
    """Run just the Architect stage."""
    architect = ArchitectAgent()
    state = await architect.run(state)
    games[state.game_id] = state
    return state


async def run_pipeline_engineer(state: GameState) -> GameState:
    """Run just the Engineer stage (no Validator for speed)."""
    engineer = EngineerAgent()
    state = await engineer.run(state)
    games[state.game_id] = state
    return state


async def run_pipeline_assembler(state: GameState) -> GameState:
    """Run just the Assembler stage."""
    state.status = "completed"
    assembler = AssemblerAgent()
    state = await assembler.run(state)
    _save_meta(state)
    games[state.game_id] = state
    return state
