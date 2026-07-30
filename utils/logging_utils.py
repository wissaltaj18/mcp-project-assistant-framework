"""Implémentation simple du LoggerPort : affiche dans la console."""

from datetime import datetime

from core.ports.logger_port import LoggerPort


class ConsoleLogger(LoggerPort):
    """Implémentation par défaut : suffisant pour le développement local."""

    def info(self, message: str) -> None:
        print(f"[{self._timestamp()}] INFO  - {message}")

    def error(self, message: str) -> None:
        print(f"[{self._timestamp()}] ERREUR - {message}")

    def _timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")