"""
Pruebas de Caja Negra
=====================
Objetivo: verificar el sistema únicamente desde la perspectiva de sus
Requerimientos Funcionales (RF01-RF12), tratando los servicios como una
caja negra. Los tests se definen por entradas y salidas esperadas, sin
conocimiento del código interno.

RF cubiertos:
  RF01 - Registrar autores
  RF02 - Registrar libros
  RF03 - Dar de baja libro
  RF04 - Registrar clientes
  RF05 - Dar de baja cliente
  RF06 - Registrar préstamo
  RF07 - Registrar devolución
  RF08 - Consultar préstamos de un cliente
  RF09 - Listar préstamos vencidos
  RF10 - Buscar y filtrar
  RF11 - Calcular fecha de devolución automáticamente
  RF12 - Actualizar estado del libro automáticamente
"""
import pytest
from datetime import date, timedelta

from src.repositories.autor_repository import AutorRepository
from src.repositories.libro_repository import LibroRepository
from src.repositories.cliente_repository import ClienteRepository
from src.repositories.prestamo_repository import PrestamoRepository
from src.services.biblioteca_service import BibliotecaService
from src.services.prestamo_service import PrestamoService
from src.models.libro import EstadoLibro
from src.models.prestamo import EstadoPrestamo
from src.exceptions import (
    AutorYaExisteError,
    LibroYaExisteError,
    LibroNoDisponibleError,
    LibroPrestadoError,
    ClienteYaExisteError,
    ClienteInactivoError,
    PrestamoYaDevueltoError,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def svc():
    a = AutorRepository()
    l = LibroRepository()
    c = ClienteRepository()
    p = PrestamoRepository()
    return (
        BibliotecaService(a, l, c, p),
        PrestamoService(l, c, p),
    )


@pytest.fixture
def svc_cargado(svc):
    bsvc, psvc = svc
    bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
    bsvc.agregar_libro("ISBN-001", "Cien años de soledad", "Sudamericana",
                       "Gabriel", "García Márquez")
    bsvc.agregar_cliente("12345678", "Juan", "Pérez")
    return bsvc, psvc


# ── RF01: Registrar autores ───────────────────────────────────────────────────

class TestCajaNegrRF01RegistrarAutor:
    def test_rf01_registrar_autor_valido(self, svc):
        bsvc, _ = svc
        autor = bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
        assert autor.nombre == "Gabriel"
        assert autor.apellido == "García Márquez"
        assert autor.nacionalidad == "Colombiana"

    def test_rf01_registrar_autor_sin_nacionalidad(self, svc):
        bsvc, _ = svc
        autor = bsvc.agregar_autor("Ana", "Karenina")
        assert autor.nacionalidad == ""

    def test_rf01_no_permite_autor_duplicado(self, svc):
        bsvc, _ = svc
        bsvc.agregar_autor("Gabriel", "García Márquez")
        with pytest.raises(AutorYaExisteError):
            bsvc.agregar_autor("Gabriel", "García Márquez")

    def test_rf01_autor_aparece_en_listado(self, svc):
        bsvc, _ = svc
        bsvc.agregar_autor("Gabriel", "García Márquez")
        autores = bsvc.obtener_autores()
        assert any(a.apellido == "García Márquez" for a in autores)


# ── RF02: Registrar libros ────────────────────────────────────────────────────

class TestCajaNegrRF02RegistrarLibro:
    def test_rf02_registrar_libro_con_autor_existente(self, svc):
        bsvc, _ = svc
        bsvc.agregar_autor("A", "B")
        libro = bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        assert libro.isbn == "ISBN-001"
        assert libro.titulo == "Título"

    def test_rf02_no_permite_isbn_duplicado(self, svc):
        bsvc, _ = svc
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        with pytest.raises(LibroYaExisteError):
            bsvc.agregar_libro("ISBN-001", "Otro título", "Ed", "A", "B")

    def test_rf02_libro_disponible_al_registrarse(self, svc):
        bsvc, _ = svc
        bsvc.agregar_autor("A", "B")
        libro = bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        assert libro.esta_disponible() is True

    def test_rf02_libro_aparece_en_listado(self, svc_cargado):
        bsvc, _ = svc_cargado
        libros = bsvc.obtener_libros()
        assert any(l.isbn == "ISBN-001" for l in libros)


# ── RF03: Dar de baja libro ───────────────────────────────────────────────────

class TestCajaNegrRF03DarDeBajaLibro:
    def test_rf03_dar_de_baja_libro_disponible(self, svc_cargado):
        bsvc, _ = svc_cargado
        bsvc.dar_de_baja_libro("ISBN-001")
        assert bsvc.obtener_libro("ISBN-001") is None

    def test_rf03_no_permite_baja_si_libro_prestado(self, svc_cargado):
        bsvc, psvc = svc_cargado
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(LibroPrestadoError):
            bsvc.dar_de_baja_libro("ISBN-001")

    def test_rf03_libro_desaparece_del_listado_tras_baja(self, svc_cargado):
        bsvc, _ = svc_cargado
        bsvc.dar_de_baja_libro("ISBN-001")
        assert all(l.isbn != "ISBN-001" for l in bsvc.obtener_libros())


# ── RF04: Registrar clientes ──────────────────────────────────────────────────

class TestCajaNegrRF04RegistrarCliente:
    def test_rf04_registrar_cliente_valido(self, svc):
        bsvc, _ = svc
        cliente = bsvc.agregar_cliente("12345678", "Juan", "Pérez")
        assert cliente.dni == "12345678"
        assert cliente.activo is True

    def test_rf04_no_permite_dni_duplicado(self, svc):
        bsvc, _ = svc
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")
        with pytest.raises(ClienteYaExisteError):
            bsvc.agregar_cliente("12345678", "Pedro", "García")

    def test_rf04_cliente_aparece_en_listado_de_activos(self, svc):
        bsvc, _ = svc
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")
        activos = bsvc.obtener_clientes_activos()
        assert any(c.dni == "12345678" for c in activos)


# ── RF05: Dar de baja cliente ─────────────────────────────────────────────────

class TestCajaNegrRF05DarDeBajaCliente:
    def test_rf05_dar_de_baja_cliente_sin_prestamos(self, svc_cargado):
        bsvc, _ = svc_cargado
        bsvc.dar_de_baja_cliente("12345678")
        cliente = bsvc.obtener_cliente("12345678")
        assert cliente.activo is False

    def test_rf05_no_permite_baja_con_prestamo_activo(self, svc_cargado):
        bsvc, psvc = svc_cargado
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(ClienteInactivoError):
            bsvc.dar_de_baja_cliente("12345678")

    def test_rf05_cliente_inactivo_no_aparece_en_activos(self, svc_cargado):
        bsvc, _ = svc_cargado
        bsvc.dar_de_baja_cliente("12345678")
        activos = bsvc.obtener_clientes_activos()
        assert all(c.dni != "12345678" for c in activos)


# ── RF06: Registrar préstamo ──────────────────────────────────────────────────

class TestCajaNegrRF06RegistrarPrestamo:
    def test_rf06_prestar_libro_disponible_a_cliente_activo(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        assert prestamo.id is not None
        assert prestamo.cliente.dni == "12345678"
        assert prestamo.libro.isbn == "ISBN-001"

    def test_rf06_no_permite_prestar_libro_no_disponible(self, svc_cargado):
        bsvc, psvc = svc_cargado
        psvc.prestar_libro("ISBN-001", "12345678")
        bsvc.agregar_cliente("87654321", "María", "González")
        with pytest.raises(LibroNoDisponibleError):
            psvc.prestar_libro("ISBN-001", "87654321")

    def test_rf06_no_permite_prestar_a_cliente_inactivo(self, svc_cargado):
        bsvc, psvc = svc_cargado
        bsvc.dar_de_baja_cliente("12345678")
        with pytest.raises(ClienteInactivoError):
            psvc.prestar_libro("ISBN-001", "12345678")


# ── RF07: Registrar devolución ────────────────────────────────────────────────

class TestCajaNegrRF07RegistrarDevolucion:
    def test_rf07_devolver_libro_prestado(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        devuelto = psvc.devolver_libro(prestamo.id)
        assert devuelto.esta_devuelto() is True

    def test_rf07_no_permite_devolver_dos_veces(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        with pytest.raises(PrestamoYaDevueltoError):
            psvc.devolver_libro(prestamo.id)

    def test_rf07_fecha_devolucion_es_hoy(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        assert prestamo.fecha_devolucion_real == date.today()


# ── RF08: Consultar préstamos de un cliente ───────────────────────────────────

class TestCajaNegrRF08PrestamosDeCliente:
    def test_rf08_listar_prestamos_activos_de_cliente(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        activos = bsvc.obtener_prestamos_activos_de_cliente("12345678")
        assert prestamo in activos

    def test_rf08_prestamo_devuelto_no_aparece_como_activo(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        activos = bsvc.obtener_prestamos_activos_de_cliente("12345678")
        assert prestamo not in activos

    def test_rf08_cliente_sin_historial_retorna_lista_vacia(self, svc):
        bsvc, _ = svc
        bsvc.agregar_cliente("11111111", "Sin", "Prestamos")
        assert bsvc.obtener_prestamos_activos_de_cliente("11111111") == []


# ── RF09: Préstamos vencidos ──────────────────────────────────────────────────

class TestCajaNegrRF09Vencidos:
    def test_rf09_prestamo_vencido_aparece_en_listado(self, repos_vencido):
        psvc, prestamo_v = repos_vencido
        vencidos = psvc.obtener_vencidos()
        assert prestamo_v in vencidos

    def test_rf09_prestamo_activo_no_aparece_como_vencido(self, svc_cargado):
        bsvc, psvc = svc_cargado
        psvc.prestar_libro("ISBN-001", "12345678")
        assert psvc.obtener_vencidos() == []

    def test_rf09_devuelto_no_aparece_como_vencido(self, repos_vencido):
        psvc, prestamo_v = repos_vencido
        psvc.devolver_libro(prestamo_v.id)
        assert psvc.obtener_vencidos() == []


@pytest.fixture
def repos_vencido():
    from src.models.autor import Autor
    from src.models.libro import Libro
    from src.models.cliente import Cliente
    from src.models.prestamo import Prestamo

    a_repo = AutorRepository()
    l_repo = LibroRepository()
    c_repo = ClienteRepository()
    p_repo = PrestamoRepository()

    autor = Autor("Test", "Vencido")
    libro = Libro("ISBN-V", "Vencido", "Ed", autor)
    cliente = Cliente("55555555", "Test", "Vencido")
    a_repo.agregar(autor)
    l_repo.agregar(libro)
    c_repo.agregar(cliente)

    ayer = date.today() - timedelta(days=1)
    hace_10 = date.today() - timedelta(days=10)
    prestamo = Prestamo(p_repo.nuevo_id(), libro, cliente, hace_10, ayer)
    libro.marcar_prestado()
    p_repo.agregar(prestamo)

    psvc = PrestamoService(l_repo, c_repo, p_repo)
    return psvc, prestamo


# ── RF10: Buscar y filtrar ────────────────────────────────────────────────────

class TestCajaNegrRF10BuscarFiltrar:
    def test_rf10_obtener_libros_disponibles(self, svc_cargado):
        bsvc, psvc = svc_cargado
        disponibles = bsvc.obtener_libros_disponibles()
        assert any(l.isbn == "ISBN-001" for l in disponibles)

    def test_rf10_libro_prestado_no_aparece_en_disponibles(self, svc_cargado):
        bsvc, psvc = svc_cargado
        psvc.prestar_libro("ISBN-001", "12345678")
        disponibles = bsvc.obtener_libros_disponibles()
        assert all(l.isbn != "ISBN-001" for l in disponibles)

    def test_rf10_obtener_clientes_activos(self, svc_cargado):
        bsvc, _ = svc_cargado
        activos = bsvc.obtener_clientes_activos()
        assert any(c.dni == "12345678" for c in activos)

    def test_rf10_buscar_autor_por_nombre(self, svc_cargado):
        bsvc, _ = svc_cargado
        autor = bsvc.buscar_autor("Gabriel", "García Márquez")
        assert autor is not None
        assert autor.nombre == "Gabriel"

    def test_rf10_buscar_autor_inexistente_retorna_none(self, svc):
        bsvc, _ = svc
        assert bsvc.buscar_autor("No", "Existe") is None


# ── RF11: Cálculo automático de fecha de devolución ──────────────────────────

class TestCajaNegrRF11FechaDevolucion:
    def test_rf11_fecha_calculada_con_dias_por_defecto(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        esperada = date.today() + timedelta(days=14)
        assert prestamo.fecha_devolucion_esperada == esperada

    def test_rf11_fecha_calculada_con_dias_personalizados(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678", dias=30)
        esperada = date.today() + timedelta(days=30)
        assert prestamo.fecha_devolucion_esperada == esperada

    def test_rf11_fecha_prestamo_es_hoy(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        assert prestamo.fecha_prestamo == date.today()

    def test_rf11_fecha_devolucion_posterior_a_fecha_prestamo(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        assert prestamo.fecha_devolucion_esperada > prestamo.fecha_prestamo


# ── RF12: Actualización automática del estado del libro ──────────────────────

class TestCajaNegrRF12EstadoLibro:
    def test_rf12_libro_pasa_a_prestado_al_prestar(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        assert prestamo.libro.estado == EstadoLibro.PRESTADO

    def test_rf12_libro_vuelve_a_disponible_al_devolver(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        assert prestamo.libro.estado == EstadoLibro.DISPONIBLE

    def test_rf12_estado_del_prestamo_es_devuelto_tras_devolucion(self, svc_cargado):
        bsvc, psvc = svc_cargado
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        assert prestamo.estado() == EstadoPrestamo.DEVUELTO
