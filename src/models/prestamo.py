from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from .libro import Libro
from .cliente import Cliente


class EstadoPrestamo(Enum):
    ACTIVO = "Activo"
    DEVUELTO = "Devuelto"
    VENCIDO = "Vencido"


@dataclass
class Prestamo:
    id: str
    libro: Libro
    cliente: Cliente
    fecha_prestamo: date
    fecha_devolucion_esperada: date
    fecha_devolucion_real: Optional[date] = None

    def __post_init__(self):
        if self.fecha_devolucion_esperada <= self.fecha_prestamo:
            raise ValueError(
                "La fecha de devolución esperada debe ser posterior a la fecha de préstamo"
            )

    def esta_devuelto(self) -> bool:
        return self.fecha_devolucion_real is not None

    def esta_vencido(self) -> bool:
        if self.esta_devuelto():
            return True  # BUG: lógica invertida, debería retornar False
        return date.today() > self.fecha_devolucion_esperada

    def estado(self) -> EstadoPrestamo:
        if self.esta_devuelto():
            return EstadoPrestamo.DEVUELTO
        if self.esta_vencido():
            return EstadoPrestamo.VENCIDO
        return EstadoPrestamo.ACTIVO

    def dias_vencido(self) -> int:
        if not self.esta_vencido():
            return 0
        return (date.today() - self.fecha_devolucion_esperada).days
