"""
Pruebas de Integración
======================
Objetivo: verificar que las capas del sistema (Modelos → Repositorios →
Servicios) interactúan correctamente entre sí. Cada test ejercita el
flujo de datos a través de al menos dos capas reales.
"""
import pytest
from datetime import date, timedelta

from src.models.libro import EstadoLibro
from src.models.prestamo import EstadoPrestamo
from src.repositories.autor_repository import AutorRepository
from src.repositories.libro_repository import LibroRepository
from src.repositories.cliente_repository import ClienteRepository
from src.repositories.prestamo_repository import PrestamoRepository
from src.services.biblioteca_service import BibliotecaService
from src.services.prestamo_service import PrestamoService
from src.exceptions import (
    AutorNoEncontradoError,
    LibroNoEncontradoError,
    LibroPrestadoError,
    LibroNoDisponibleError,
    ClienteNoEncontradoError,
    ClienteInactivoError,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def repos():
    return (
        AutorRepository(),
        LibroRepository(),
        ClienteRepository(),
        PrestamoRepository(),
    )


@pytest.fixture
def servicios(repos):
    a_repo, l_repo, c_repo, p_repo = repos
    bsvc = BibliotecaService(a_repo, l_repo, c_repo, p_repo)
    psvc = PrestamoService(l_repo, c_repo, p_repo)
    return bsvc, psvc


@pytest.fixture
def sistema_basico(servicios):
    bsvc, psvc = servicios
    bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
    bsvc.agregar_libro("ISBN-001", "Cien años de soledad", "Sudamericana",
                       "Gabriel", "García Márquez")
    bsvc.agregar_cliente("12345678", "Juan", "Pérez")
    return bsvc, psvc


# ── Integración: Autores y Libros ─────────────────────────────────────────────

class TestIntegracionAutorLibro:
    def test_agregar_libro_requiere_autor_existente(self, servicios):
        bsvc, _ = servicios
        with pytest.raises(AutorNoEncontradoError):
            bsvc.agregar_libro("ISBN-001", "Título", "Ed", "No", "Existe")

    def test_agregar_libro_con_autor_registrado(self, servicios):
        bsvc, _ = servicios
        bsvc.agregar_autor("Ana", "Karenina")
        libro = bsvc.agregar_libro("ISBN-001", "Título", "Ed", "Ana", "Karenina")
        assert libro.autor.nombre == "Ana"
        assert libro.autor.apellido == "Karenina"

    def test_libro_referencia_el_mismo_objeto_autor(self, servicios):
        bsvc, _ = servicios
        bsvc.agregar_autor("Ana", "Karenina")
        libro = bsvc.agregar_libro("ISBN-001", "Título", "Ed", "Ana", "Karenina")
        autor_en_repo = bsvc.buscar_autor("Ana", "Karenina")
        assert libro.autor is autor_en_repo

    def test_dar_de_baja_libro_disponible(self, sistema_basico):
        bsvc, _ = sistema_basico
        bsvc.dar_de_baja_libro("ISBN-001")
        assert bsvc.obtener_libro("ISBN-001") is None

    def test_dar_de_baja_libro_prestado_lanza_error(self, sistema_basico):
        bsvc, psvc = sistema_basico
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(LibroPrestadoError):
            bsvc.dar_de_baja_libro("ISBN-001")

    def test_dar_de_baja_libro_inexistente_lanza_error(self, servicios):
        bsvc, _ = servicios
        with pytest.raises(LibroNoEncontradoError):
            bsvc.dar_de_baja_libro("ISBN-NO-EXISTE")


# ── Integración: Clientes y Préstamos ─────────────────────────────────────────

class TestIntegracionClientePrestamo:
    def test_dar_de_baja_cliente_con_prestamo_activo_lanza_error(self, sistema_basico):
        bsvc, psvc = sistema_basico
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(ClienteInactivoError):
            bsvc.dar_de_baja_cliente("12345678")

    def test_dar_de_baja_cliente_tras_devolucion(self, sistema_basico):
        bsvc, psvc = sistema_basico
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        bsvc.dar_de_baja_cliente("12345678")
        cliente = bsvc.obtener_cliente("12345678")
        assert cliente.activo is False

    def test_dar_de_baja_cliente_inexistente_lanza_error(self, servicios):
        bsvc, _ = servicios
        with pytest.raises(ClienteNoEncontradoError):
            bsvc.dar_de_baja_cliente("99999999")

    def test_prestamos_activos_de_cliente(self, sistema_basico):
        bsvc, psvc = sistema_basico
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        activos = bsvc.obtener_prestamos_activos_de_cliente("12345678")
        assert prestamo in activos

    def test_prestamos_activos_vacio_tras_devolucion(self, sistema_basico):
        bsvc, psvc = sistema_basico
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        activos = bsvc.obtener_prestamos_activos_de_cliente("12345678")
        assert activos == []

    def test_prestamos_activos_cliente_inexistente_lanza_error(self, servicios):
        bsvc, _ = servicios
        with pytest.raises(ClienteNoEncontradoError):
            bsvc.obtener_prestamos_activos_de_cliente("NO-EXISTE")


# ── Integración: Ciclo completo de préstamo ───────────────────────────────────

class TestIntegracionCicloPrestamo:
    def test_ciclo_completo_prestamo_y_devolucion(self, sistema_basico):
        bsvc, psvc = sistema_basico

        # 1. El libro está disponible
        assert bsvc.obtener_libro("ISBN-001").esta_disponible() is True

        # 2. Se realiza el préstamo
        prestamo = psvc.prestar_libro("ISBN-001", "12345678", dias=14)
        assert prestamo.id == "P0001"
        assert prestamo.libro.estado == EstadoLibro.PRESTADO

        # 3. El libro ya no aparece como disponible
        assert bsvc.obtener_libros_disponibles() == []

        # 4. El préstamo aparece como activo
        assert psvc.obtener_prestamos_activos() != []

        # 5. Se devuelve
        psvc.devolver_libro(prestamo.id)
        assert prestamo.esta_devuelto() is True
        assert prestamo.libro.estado == EstadoLibro.DISPONIBLE

        # 6. El libro vuelve a estar disponible
        assert len(bsvc.obtener_libros_disponibles()) == 1

        # 7. No hay préstamos activos
        assert psvc.obtener_prestamos_activos() == []

    def test_prestar_libro_recien_devuelto(self, sistema_basico):
        bsvc, psvc = sistema_basico
        p1 = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(p1.id)

        bsvc.agregar_cliente("87654321", "María", "González")
        p2 = psvc.prestar_libro("ISBN-001", "87654321")
        assert p2.libro.estado == EstadoLibro.PRESTADO

    def test_un_libro_no_puede_prestarse_dos_veces(self, sistema_basico):
        bsvc, psvc = sistema_basico
        bsvc.agregar_cliente("87654321", "María", "González")
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(LibroNoDisponibleError):
            psvc.prestar_libro("ISBN-001", "87654321")

    def test_multiples_libros_multiples_clientes(self, servicios):
        bsvc, psvc = servicios
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-1", "Libro 1", "Ed", "A", "B")
        bsvc.agregar_libro("ISBN-2", "Libro 2", "Ed", "A", "B")
        bsvc.agregar_cliente("11111111", "Cliente", "Uno")
        bsvc.agregar_cliente("22222222", "Cliente", "Dos")

        p1 = psvc.prestar_libro("ISBN-1", "11111111")
        p2 = psvc.prestar_libro("ISBN-2", "22222222")

        assert p1.cliente.dni == "11111111"
        assert p2.cliente.dni == "22222222"
        assert len(psvc.obtener_prestamos_activos()) == 2

    def test_fecha_devolucion_calculada_correctamente(self, sistema_basico):
        _, psvc = sistema_basico
        prestamo = psvc.prestar_libro("ISBN-001", "12345678", dias=21)
        esperada = date.today() + timedelta(days=21)
        assert prestamo.fecha_devolucion_esperada == esperada

    def test_estado_prestamo_actualiza_segun_devolucion(self, sistema_basico):
        _, psvc = sistema_basico
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        assert prestamo.estado() == EstadoPrestamo.ACTIVO
        psvc.devolver_libro(prestamo.id)
        assert prestamo.estado() == EstadoPrestamo.DEVUELTO

    def test_prestamo_vencido_desaparece_tras_devolucion(
        self, repos, servicios
    ):
        bsvc, psvc = servicios
        a_repo, l_repo, c_repo, p_repo = repos

        from src.models.autor import Autor
        from src.models.libro import Libro
        from src.models.cliente import Cliente
        from src.models.prestamo import Prestamo

        autor = Autor("X", "Y")
        libro = Libro("ISBN-V", "Vencido", "Ed", autor)
        cliente = Cliente("55555555", "Vencido", "Cliente")
        a_repo.agregar(autor)
        l_repo.agregar(libro)
        c_repo.agregar(cliente)

        ayer = date.today() - timedelta(days=1)
        hace_10 = date.today() - timedelta(days=10)
        p = Prestamo(p_repo.nuevo_id(), libro, cliente, hace_10, ayer)
        libro.marcar_prestado()
        p_repo.agregar(p)

        assert p in psvc.obtener_vencidos()
        psvc.devolver_libro(p.id)
        assert p not in psvc.obtener_vencidos()
