from dataclasses import dataclass

@dataclass
class AIAgent:
    """Simple representation of an AI agent."""
    name: str
    running: bool = False

    def start(self) -> None:
        """Mark the agent as running."""
        self.running = True

    def stop(self) -> None:
        """Mark the agent as stopped."""
        self.running = False

    @property
    def status(self) -> str:
        """Return the current status of the agent."""
        return "работает" if self.running else "остановлен"
