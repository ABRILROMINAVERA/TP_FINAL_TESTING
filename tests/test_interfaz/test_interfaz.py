"""
Pruebas de Interfaz
===================
Objetivo: verificar los contratos de interfaz entre las capas del
sistema usando objetos mock. Se comprueba que:
  - Los servicios invocan los métodos correctos de los repositorios.
  - Los argumentos pasados entre capas son los esperados.
  - Las excepciones de repositorio se propagan correctamente.
  - Los valores de retorno de los servicios cumplen el tipo y contenido
    esperados por sus consumidores.

Se usa unittest.mock.MagicMock para aislar cada capa de sus dependencias.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, call

from src.models.autor import Autor
from src.models.libro import Libro, EstadoLibro
from src.models.cliente import Cliente
from src.models.prestamo import Prestamo, EstadoPrestamo
from src.services.biblioteca_service import BibliotecaService
from src.services.prestamo_service import PrestamoService
from src.exceptions import (
    AutorNoEncontradoError,
    LibroNoEncontradoError,
    LibroNoDisponibleError,
    LibroPrestadoError,
    ClienteNoEncontradoError,
    ClienteInactivoError,
    PrestamoNoEncontradoError,
    PrestamoYaDevueltoError,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _autor():
    return Autor("Gabriel", "García Márquez", "Colombiana")


def _libro(autor=None):
    return Libro("ISBN-001", "Cien años de soledad", "Sudamericana",
                 autor or _autor())


def _cliente():
    return Cliente("12345678", "Juan", "Pérez")


def _prestamo(libro=None, cliente=None):
    hoy = date.today()
    return Prestamo(
        id="P0001",
        libro=libro or _libro(),
        cliente=cliente or _cliente(),
        fecha_prestamo=hoy,
        fecha_devolucion_esperada=hoy + timedelta(days=14),
    )


# ── Interfaz: BibliotecaService → AutorRepository ────────────────────────────

class TestInterfazBibliotecaServiceAutores:
    def test_agregar_autor_llama_a_repo_agregar(self):
        autor_repo = MagicMock()
        svc = BibliotecaService(autor_repo, MagicMock(), MagicMock(), MagicMock())

        svc.agregar_autor("Gabriel", "García Márquez", "Colombiana")

        autor_repo.agregar.assert_called_once()
        arg = autor_repo.agregar.call_args[0][0]
        assert isinstance(arg, Autor)
        assert arg.nombre == "Gabriel"

    def test_obtener_autores_delega_a_repo_obtener_todos(self):
        autor_repo = MagicMock()
        autor_repo.obtener_todos.return_value = [_autor()]
        svc = BibliotecaService(autor_repo, MagicMock(), MagicMock(), MagicMock())

        resultado = svc.obtener_autores()

        autor_repo.obtener_todos.assert_called_once()
        assert len(resultado) == 1

    def test_buscar_autor_delega_a_repo_buscar(self):
        autor_repo = MagicMock()
        autor_repo.buscar.return_value = _autor()
        svc = BibliotecaService(autor_repo, MagicMock(), MagicMock(), MagicMock())

        resultado = svc.buscar_autor("Gabriel", "García Márquez")

        autor_repo.buscar.assert_called_once_with("Gabriel", "García Márquez")
        assert resultado.nombre == "Gabriel"


# ── Interfaz: BibliotecaService → LibroRepository ────────────────────────────

class TestInterfazBibliotecaServiceLibros:
    def test_agregar_libro_consulta_autor_antes_de_agregar(self):
        autor_repo = MagicMock()
        libro_repo = MagicMock()
        autor_repo.buscar.return_value = _autor()
        svc = BibliotecaService(autor_repo, libro_repo, MagicMock(), MagicMock())

        svc.agregar_libro("ISBN-001", "Título", "Ed", "Gabriel", "García Márquez")

        autor_repo.buscar.assert_called_once_with("Gabriel", "García Márquez")
        libro_repo.agregar.assert_called_once()

    def test_agregar_libro_lanza_error_si_autor_no_existe(self):
        autor_repo = MagicMock()
        autor_repo.buscar.return_value = None
        svc = BibliotecaService(autor_repo, MagicMock(), MagicMock(), MagicMock())

        with pytest.raises(AutorNoEncontradoError):
            svc.agregar_libro("ISBN-001", "Título", "Ed", "No", "Existe")

    def test_dar_de_baja_libro_llama_eliminar_en_repo(self):
        libro_repo = MagicMock()
        libro = _libro()
        libro_repo.obtener_por_isbn.return_value = libro
        svc = BibliotecaService(MagicMock(), libro_repo, MagicMock(), MagicMock())

        svc.dar_de_baja_libro("ISBN-001")

        libro_repo.eliminar.assert_called_once_with("ISBN-001")

    def test_dar_de_baja_libro_prestado_no_llama_eliminar(self):
        libro_repo = MagicMock()
        libro = _libro()
        libro.marcar_prestado()
        libro_repo.obtener_por_isbn.return_value = libro
        svc = BibliotecaService(MagicMock(), libro_repo, MagicMock(), MagicMock())

        with pytest.raises(LibroPrestadoError):
            svc.dar_de_baja_libro("ISBN-001")

        libro_repo.eliminar.assert_not_called()

    def test_obtener_libros_disponibles_delega_a_repo(self):
        libro_repo = MagicMock()
        libro_repo.obtener_disponibles.return_value = [_libro()]
        svc = BibliotecaService(MagicMock(), libro_repo, MagicMock(), MagicMock())

        resultado = svc.obtener_libros_disponibles()

        libro_repo.obtener_disponibles.assert_called_once()
        assert len(resultado) == 1


# ── Interfaz: BibliotecaService → ClienteRepository ──────────────────────────

class TestInterfazBibliotecaServiceClientes:
    def test_agregar_cliente_llama_a_repo_agregar(self):
        cliente_repo = MagicMock()
        svc = BibliotecaService(MagicMock(), MagicMock(), cliente_repo, MagicMock())

        svc.agregar_cliente("12345678", "Juan", "Pérez")

        cliente_repo.agregar.assert_called_once()
        arg = cliente_repo.agregar.call_args[0][0]
        assert isinstance(arg, Cliente)
        assert arg.dni == "12345678"

    def test_dar_de_baja_cliente_consulta_prestamos_pendientes(self):
        cliente_repo = MagicMock()
        prestamo_repo = MagicMock()
        cliente = _cliente()
        cliente_repo.obtener_por_dni.return_value = cliente
        prestamo_repo.obtener_por_cliente.return_value = []
        svc = BibliotecaService(MagicMock(), MagicMock(), cliente_repo, prestamo_repo)

        svc.dar_de_baja_cliente("12345678")

        prestamo_repo.obtener_por_cliente.assert_called_once_with("12345678")

    def test_dar_de_baja_cliente_inexistente_lanza_error(self):
        cliente_repo = MagicMock()
        cliente_repo.obtener_por_dni.return_value = None
        svc = BibliotecaService(MagicMock(), MagicMock(), cliente_repo, MagicMock())

        with pytest.raises(ClienteNoEncontradoError):
            svc.dar_de_baja_cliente("99999999")


# ── Interfaz: PrestamoService → repositorios ─────────────────────────────────

class TestInterfazPrestamoService:
    def test_prestar_libro_consulta_isbn_y_dni(self):
        libro_repo = MagicMock()
        cliente_repo = MagicMock()
        prestamo_repo = MagicMock()

        libro = _libro()
        cliente = _cliente()
        libro_repo.obtener_por_isbn.return_value = libro
        cliente_repo.obtener_por_dni.return_value = cliente
        prestamo_repo.nuevo_id.return_value = "P0001"

        svc = PrestamoService(libro_repo, cliente_repo, prestamo_repo)
        svc.prestar_libro("ISBN-001", "12345678", dias=14)

        libro_repo.obtener_por_isbn.assert_called_once_with("ISBN-001")
        cliente_repo.obtener_por_dni.assert_called_once_with("12345678")

    def test_prestar_libro_llama_agregar_en_prestamo_repo(self):
        libro_repo = MagicMock()
        cliente_repo = MagicMock()
        prestamo_repo = MagicMock()

        libro_repo.obtener_por_isbn.return_value = _libro()
        cliente_repo.obtener_por_dni.return_value = _cliente()
        prestamo_repo.nuevo_id.return_value = "P0001"

        svc = PrestamoService(libro_repo, cliente_repo, prestamo_repo)
        svc.prestar_libro("ISBN-001", "12345678")

        prestamo_repo.agregar.assert_called_once()
        arg = prestamo_repo.agregar.call_args[0][0]
        assert isinstance(arg, Prestamo)

    def test_prestar_lanza_error_si_libro_no_encontrado(self):
        libro_repo = MagicMock()
        libro_repo.obtener_por_isbn.return_value = None
        svc = PrestamoService(libro_repo, MagicMock(), MagicMock())

        with pytest.raises(LibroNoEncontradoError):
            svc.prestar_libro("ISBN-NO-EXISTE", "12345678")

    def test_prestar_lanza_error_si_libro_no_disponible(self):
        libro_repo = MagicMock()
        libro = _libro()
        libro.marcar_prestado()
        libro_repo.obtener_por_isbn.return_value = libro
        svc = PrestamoService(libro_repo, MagicMock(), MagicMock())

        with pytest.raises(LibroNoDisponibleError):
            svc.prestar_libro("ISBN-001", "12345678")

    def test_prestar_lanza_error_si_cliente_no_encontrado(self):
        libro_repo = MagicMock()
        cliente_repo = MagicMock()
        libro_repo.obtener_por_isbn.return_value = _libro()
        cliente_repo.obtener_por_dni.return_value = None
        svc = PrestamoService(libro_repo, cliente_repo, MagicMock())

        with pytest.raises(ClienteNoEncontradoError):
            svc.prestar_libro("ISBN-001", "99999999")

    def test_prestar_lanza_error_si_cliente_inactivo(self):
        libro_repo = MagicMock()
        cliente_repo = MagicMock()
        libro_repo.obtener_por_isbn.return_value = _libro()
        cliente = _cliente()
        cliente.dar_de_baja()
        cliente_repo.obtener_por_dni.return_value = cliente
        svc = PrestamoService(libro_repo, cliente_repo, MagicMock())

        with pytest.raises(ClienteInactivoError):
            svc.prestar_libro("ISBN-001", "12345678")

    def test_devolver_libro_consulta_prestamo_por_id(self):
        prestamo_repo = MagicMock()
        prestamo = _prestamo()
        prestamo_repo.obtener_por_id.return_value = prestamo
        svc = PrestamoService(MagicMock(), MagicMock(), prestamo_repo)

        svc.devolver_libro("P0001")

        prestamo_repo.obtener_por_id.assert_called_once_with("P0001")

    def test_devolver_lanza_error_si_prestamo_no_existe(self):
        prestamo_repo = MagicMock()
        prestamo_repo.obtener_por_id.return_value = None
        svc = PrestamoService(MagicMock(), MagicMock(), prestamo_repo)

        with pytest.raises(PrestamoNoEncontradoError):
            svc.devolver_libro("P9999")

    def test_devolver_lanza_error_si_ya_devuelto(self):
        prestamo_repo = MagicMock()
        prestamo = _prestamo()
        prestamo.fecha_devolucion_real = date.today()
        prestamo_repo.obtener_por_id.return_value = prestamo
        svc = PrestamoService(MagicMock(), MagicMock(), prestamo_repo)

        with pytest.raises(PrestamoYaDevueltoError):
            svc.devolver_libro("P0001")


# ── Interfaz: tipos de retorno ────────────────────────────────────────────────

class TestInterfazTiposDeRetorno:
    def test_prestar_retorna_objeto_prestamo(self):
        libro_repo = MagicMock()
        cliente_repo = MagicMock()
        prestamo_repo = MagicMock()
        libro_repo.obtener_por_isbn.return_value = _libro()
        cliente_repo.obtener_por_dni.return_value = _cliente()
        prestamo_repo.nuevo_id.return_value = "P0001"
        svc = PrestamoService(libro_repo, cliente_repo, prestamo_repo)

        resultado = svc.prestar_libro("ISBN-001", "12345678")

        assert isinstance(resultado, Prestamo)

    def test_devolver_retorna_objeto_prestamo(self):
        prestamo_repo = MagicMock()
        prestamo = _prestamo()
        prestamo_repo.obtener_por_id.return_value = prestamo
        svc = PrestamoService(MagicMock(), MagicMock(), prestamo_repo)

        resultado = svc.devolver_libro("P0001")

        assert isinstance(resultado, Prestamo)

    def test_obtener_prestamos_retorna_lista(self):
        prestamo_repo = MagicMock()
        prestamo_repo.obtener_todos.return_value = [_prestamo()]
        svc = PrestamoService(MagicMock(), MagicMock(), prestamo_repo)

        resultado = svc.obtener_prestamos()

        assert isinstance(resultado, list)

    def test_obtener_autores_retorna_lista(self):
        autor_repo = MagicMock()
        autor_repo.obtener_todos.return_value = [_autor()]
        svc = BibliotecaService(autor_repo, MagicMock(), MagicMock(), MagicMock())

        resultado = svc.obtener_autores()

        assert isinstance(resultado, list)
