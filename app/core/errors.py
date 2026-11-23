"""Errores de dominio compartidos por los módulos del núcleo."""


class GameRuleError(Exception):
    """Acción rechazada por las reglas del juego (turno, fase, carta inexistente...)."""


class NotFoundError(Exception):
    """La partida, la sala o el jugador solicitado no existe."""


class StaleStateError(Exception):
    """R2: la jugada se envió sobre una versión desactualizada del estado."""

    def __init__(self, current_version: int) -> None:
        super().__init__(
            f"El estado cambió (versión actual {current_version}). Se reenvía el estado vigente."
        )
        self.current_version = current_version


class ConcurrencyError(Exception):
    """ADR-05: otra acción tiene el cerrojo de la partida (SET NX); reintentar."""
