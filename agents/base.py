"""Abstract base class for all pipeline agents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from models import GameState


class BaseAgent(ABC):
    """Base class that every pipeline agent must extend."""

    name: str = "base"

    @abstractmethod
    async def run(self, state: GameState) -> GameState:
        """Process the game state and return the updated state."""
        ...

    def log(self, message: str) -> None:
        """Emit a log line prefixed with the agent name."""
        print(f"[{self.name}] {message}")
