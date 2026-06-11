from datetime import date, timedelta
from typing import List

from ..models.prestamo import Prestamo
from ..repositories.libro_repository import LibroRepository
from ..repositories.cliente_repository import ClienteRepository
from ..repositories.prestamo_repository import PrestamoRepository
from ..exceptions import (
    LibroNoEncontradoError,
    LibroNoDisponibleError,
    ClienteNoEncontradoError,
    ClienteInactivoError,
    PrestamoNoEncontradoError,
    PrestamoYaDevueltoError,
)

DIAS_PRESTAMO_DEFAULT = 14


class PrestamoService:
    def __init__(
        self,
        libro_repo: LibroRepository,
        cliente_repo: ClienteRepository,
        prestamo_repo: PrestamoRepository,
    ):
        self._libros = libro_repo
        self._clientes = cliente_repo
        self._prestamos = prestamo_repo

    def prestar_libro(
        self, isbn: str, dni: str, dias: int = DIAS_PRESTAMO_DEFAULT
    ) -> Prestamo:
        libro = self._libros.obtener_por_isbn(isbn)
        if libro is None:
            raise LibroNoEncontradoError(
                f"No se encontró el libro con ISBN '{isbn}'"
            )
        if not libro.esta_disponible():
            raise LibroNoDisponibleError(
                f"El libro '{libro.titulo}' no está disponible para préstamo"
            )

        cliente = self._clientes.obtener_por_dni(dni)
        if cliente is None:
            raise ClienteNoEncontradoError(
                f"No se encontró el cliente con DNI '{dni}'"
            )
        if not cliente.activo:
            raise ClienteInactivoError(
                f"El cliente '{cliente.nombre_completo()}' no está activo"
            )

        hoy = date.today()
        prestamo = Prestamo(
            id=self._prestamos.nuevo_id(),
            libro=libro,
            cliente=cliente,
            fecha_prestamo=hoy,
            fecha_devolucion_esperada=hoy + timedelta(days=1),  # BUG: ignora el parámetro dias
        )

        libro.marcar_prestado()
        self._prestamos.agregar(prestamo)
        return prestamo

    def devolver_libro(self, prestamo_id: str) -> Prestamo:
        prestamo = self._prestamos.obtener_por_id(prestamo_id)
        if prestamo is None:
            raise PrestamoNoEncontradoError(
                f"No se encontró el préstamo con ID '{prestamo_id}'"
            )
        if prestamo.esta_devuelto():
            raise PrestamoYaDevueltoError(
                f"El préstamo '{prestamo_id}' ya fue devuelto"
            )
        prestamo.fecha_devolucion_real = date.today()
        # BUG: no llama a marcar_disponible(), el libro queda en estado PRESTADO
        return prestamo

    def obtener_prestamos(self) -> List[Prestamo]:
        return self._prestamos.obtener_todos()

    def obtener_prestamos_activos(self) -> List[Prestamo]:
        return self._prestamos.obtener_activos()

    def obtener_vencidos(self) -> List[Prestamo]:
        return self._prestamos.obtener_vencidos()

    def obtener_prestamos_de_cliente(self, dni: str) -> List[Prestamo]:
        return self._prestamos.obtener_por_cliente(dni)
