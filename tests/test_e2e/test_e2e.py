"""
Pruebas End-to-End (E2E)
========================
Objetivo: verificar escenarios completos de uso del sistema tal como
los ejecutaría un bibliotecario real, atravesando todas las capas
(Servicios → Repositorios → Modelos) sin ningún mock.

Cada test representa un caso de uso de punta a punta y valida el estado
del sistema en cada paso del flujo, no solo al final.

Escenarios:
  E2E-01  Alta completa de entidades y primer préstamo
  E2E-02  Ciclo completo de préstamo, devolución y re-préstamo
  E2E-03  Intento de préstamo sobre libro ya prestado
  E2E-04  Baja de cliente bloqueada por préstamo activo → devolver → dar de baja
  E2E-05  Detección y resolución de préstamos vencidos
  E2E-06  Cliente con múltiples libros prestados simultáneamente
  E2E-07  Integridad ante registros duplicados en toda la cadena
  E2E-08  Baja de libro bloqueada por préstamo activo → devolver → dar de baja
  E2E-09  Sistema vacío responde correctamente en todas las consultas
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
from src.models.autor import Autor
from src.models.libro import Libro
from src.models.cliente import Cliente
from src.models.prestamo import Prestamo
from src.exceptions import (
    AutorYaExisteError,
    LibroYaExisteError,
    LibroNoDisponibleError,
    LibroPrestadoError,
    ClienteYaExisteError,
    ClienteInactivoError,
    PrestamoYaDevueltoError,
)


# ── Fixture: sistema vacío ────────────────────────────────────────────────────

@pytest.fixture
def sistema():
    """Sistema limpio con todas las capas reales instanciadas."""
    a_repo = AutorRepository()
    l_repo = LibroRepository()
    c_repo = ClienteRepository()
    p_repo = PrestamoRepository()
    bsvc = BibliotecaService(a_repo, l_repo, c_repo, p_repo)
    psvc = PrestamoService(l_repo, c_repo, p_repo)
    return bsvc, psvc, a_repo, l_repo, c_repo, p_repo


# ── E2E-01: Alta completa de entidades y primer préstamo ─────────────────────

class TestE2E01AltaCompletaYPrimerPrestamo:
    """
    Escenario: el bibliotecario registra por primera vez un autor, un libro,
    un cliente y realiza el primer préstamo del sistema.
    Verifica que cada entidad queda correctamente registrada en su capa
    y que el estado del sistema es consistente en todos los niveles.
    """

    def test_sistema_vacio_al_inicio(self, sistema):
        bsvc, psvc, *_ = sistema
        assert bsvc.obtener_autores() == []
        assert bsvc.obtener_libros() == []
        assert bsvc.obtener_clientes() == []
        assert psvc.obtener_prestamos() == []

    def test_registrar_autor(self, sistema):
        bsvc, *_ = sistema
        autor = bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
        assert autor.nombre == "Gabriel"
        assert autor.apellido == "García Márquez"
        assert autor.nacionalidad == "Colombiana"
        assert len(bsvc.obtener_autores()) == 1

    def test_registrar_libro_vinculado_a_autor(self, sistema):
        bsvc, *_ = sistema
        bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
        libro = bsvc.agregar_libro(
            "ISBN-001", "Cien años de soledad", "Sudamericana",
            "Gabriel", "García Márquez"
        )
        assert libro.isbn == "ISBN-001"
        assert libro.autor.nombre == "Gabriel"
        assert libro.esta_disponible() is True
        assert len(bsvc.obtener_libros()) == 1
        assert len(bsvc.obtener_libros_disponibles()) == 1

    def test_registrar_cliente(self, sistema):
        bsvc, *_ = sistema
        cliente = bsvc.agregar_cliente("12345678", "Juan", "Pérez")
        assert cliente.dni == "12345678"
        assert cliente.activo is True
        assert len(bsvc.obtener_clientes()) == 1
        assert len(bsvc.obtener_clientes_activos()) == 1

    def test_flujo_completo_alta_y_prestamo(self, sistema):
        bsvc, psvc, *_ = sistema

        # Paso 1: registrar entidades
        bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
        bsvc.agregar_libro("ISBN-001", "Cien años de soledad", "Sudamericana",
                           "Gabriel", "García Márquez")
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")

        # Paso 2: verificar estado previo al préstamo
        assert len(bsvc.obtener_libros_disponibles()) == 1
        assert len(bsvc.obtener_clientes_activos()) == 1

        # Paso 3: realizar el préstamo
        prestamo = psvc.prestar_libro("ISBN-001", "12345678", dias=14)

        # Paso 4: verificar estado posterior en todas las capas
        assert prestamo.id == "P0001"
        assert prestamo.libro.estado == EstadoLibro.PRESTADO
        assert prestamo.cliente.dni == "12345678"
        assert prestamo.fecha_prestamo == date.today()
        assert prestamo.fecha_devolucion_esperada == date.today() + timedelta(days=14)
        assert prestamo.estado() == EstadoPrestamo.ACTIVO

        # Paso 5: verificar consistencia del sistema
        assert bsvc.obtener_libros_disponibles() == []
        assert len(psvc.obtener_prestamos_activos()) == 1
        assert prestamo in bsvc.obtener_prestamos_activos_de_cliente("12345678")


# ── E2E-02: Ciclo completo de préstamo, devolución y re-préstamo ──────────────

class TestE2E02CicloPrestamoDevolucionReprestamo:
    """
    Escenario: un libro es prestado, devuelto y vuelto a prestar a otro cliente,
    verificando que el estado es consistente en cada transición.
    """

    @pytest.fixture
    def sistema_cargado(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("Jorge Luis", "Borges", "Argentina")
        bsvc.agregar_libro("ISBN-002", "Ficciones", "Sur", "Jorge Luis", "Borges")
        bsvc.agregar_cliente("11111111", "Ana", "García")
        bsvc.agregar_cliente("22222222", "Luis", "Martínez")
        return bsvc, psvc

    def test_libro_disponible_antes_del_prestamo(self, sistema_cargado):
        bsvc, _ = sistema_cargado
        assert bsvc.obtener_libro("ISBN-002").esta_disponible() is True

    def test_libro_no_disponible_durante_prestamo(self, sistema_cargado):
        bsvc, psvc = sistema_cargado
        psvc.prestar_libro("ISBN-002", "11111111")
        assert bsvc.obtener_libro("ISBN-002").esta_disponible() is False
        assert bsvc.obtener_libros_disponibles() == []

    def test_libro_disponible_tras_devolucion(self, sistema_cargado):
        bsvc, psvc = sistema_cargado
        prestamo = psvc.prestar_libro("ISBN-002", "11111111")
        psvc.devolver_libro(prestamo.id)
        assert bsvc.obtener_libro("ISBN-002").esta_disponible() is True
        assert len(bsvc.obtener_libros_disponibles()) == 1

    def test_represtamo_a_segundo_cliente(self, sistema_cargado):
        bsvc, psvc = sistema_cargado

        # Cliente 1 pide y devuelve
        p1 = psvc.prestar_libro("ISBN-002", "11111111")
        psvc.devolver_libro(p1.id)

        # Cliente 2 lo pide
        p2 = psvc.prestar_libro("ISBN-002", "22222222")

        assert p2.cliente.dni == "22222222"
        assert p2.libro.estado == EstadoLibro.PRESTADO
        assert p1.esta_devuelto() is True
        assert p2.esta_devuelto() is False

    def test_historial_completo_tras_ciclo(self, sistema_cargado):
        bsvc, psvc = sistema_cargado
        p1 = psvc.prestar_libro("ISBN-002", "11111111")
        psvc.devolver_libro(p1.id)
        p2 = psvc.prestar_libro("ISBN-002", "22222222")

        todos = psvc.obtener_prestamos()
        assert len(todos) == 2
        assert p1 in todos
        assert p2 in todos
        assert len(psvc.obtener_prestamos_activos()) == 1


# ── E2E-03: Intento de préstamo sobre libro ya prestado ───────────────────────

class TestE2E03PrestamoSobreLibroPrestado:
    """
    Escenario: dos clientes intentan pedir el mismo libro. El segundo
    intento debe ser rechazado y el estado del sistema no debe alterarse.
    """

    def test_segundo_cliente_no_puede_pedir_libro_prestado(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        bsvc.agregar_cliente("11111111", "Cliente", "Uno")
        bsvc.agregar_cliente("22222222", "Cliente", "Dos")

        psvc.prestar_libro("ISBN-001", "11111111")

        with pytest.raises(LibroNoDisponibleError):
            psvc.prestar_libro("ISBN-001", "22222222")

    def test_estado_sistema_intacto_tras_rechazo(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        bsvc.agregar_cliente("11111111", "Cliente", "Uno")
        bsvc.agregar_cliente("22222222", "Cliente", "Dos")

        p1 = psvc.prestar_libro("ISBN-001", "11111111")

        try:
            psvc.prestar_libro("ISBN-001", "22222222")
        except LibroNoDisponibleError:
            pass

        # El sistema debe conservar el estado original
        assert len(psvc.obtener_prestamos()) == 1
        assert psvc.obtener_prestamos()[0].cliente.dni == "11111111"
        assert bsvc.obtener_libro("ISBN-001").estado == EstadoLibro.PRESTADO
        assert psvc.obtener_prestamos_de_cliente("22222222") == []


# ── E2E-04: Baja de cliente bloqueada → devolver → dar de baja ────────────────

class TestE2E04BajaClienteConPrestamo:
    """
    Escenario: el bibliotecario intenta dar de baja a un cliente que tiene
    un préstamo activo. El sistema lo rechaza. Luego el cliente devuelve
    el libro y la baja se completa exitosamente.
    """

    def test_flujo_completo_baja_cliente(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")

        # Paso 1: cliente pide libro
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        assert prestamo.estado() == EstadoPrestamo.ACTIVO

        # Paso 2: intento de baja → rechazado
        with pytest.raises(ClienteInactivoError):
            bsvc.dar_de_baja_cliente("12345678")

        # Paso 3: cliente devuelve el libro
        psvc.devolver_libro(prestamo.id)
        assert prestamo.esta_devuelto() is True

        # Paso 4: ahora la baja procede
        bsvc.dar_de_baja_cliente("12345678")

        # Paso 5: verificar estado final en todas las capas
        cliente = bsvc.obtener_cliente("12345678")
        assert cliente.activo is False
        assert bsvc.obtener_clientes_activos() == []
        assert bsvc.obtener_libro("ISBN-001").esta_disponible() is True

    def test_cliente_dado_de_baja_no_puede_recibir_prestamo(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")
        bsvc.dar_de_baja_cliente("12345678")

        with pytest.raises(ClienteInactivoError):
            psvc.prestar_libro("ISBN-001", "12345678")


# ── E2E-05: Detección y resolución de préstamos vencidos ─────────────────────

class TestE2E05PrestamosVencidos:
    """
    Escenario: el sistema tiene préstamos activos y vencidos. El bibliotecario
    consulta los vencidos, registra la devolución de uno y verifica que
    desaparece del listado.
    """

    @pytest.fixture
    def sistema_con_vencidos(self, sistema):
        bsvc, psvc, a_repo, l_repo, c_repo, p_repo = sistema
        bsvc.agregar_autor("A", "B")

        # Libro 1: préstamo activo (vence en 7 días)
        bsvc.agregar_libro("ISBN-ACT", "Activo", "Ed", "A", "B")
        bsvc.agregar_cliente("11111111", "Cliente", "Activo")
        p_activo = psvc.prestar_libro("ISBN-ACT", "11111111", dias=7)

        # Libro 2: préstamo vencido (inserción directa con fecha pasada)
        libro_v = Libro("ISBN-VEN", "Vencido", "Ed",
                        bsvc.buscar_autor("A", "B"))
        cliente_v = Cliente("22222222", "Cliente", "Vencido")
        l_repo.agregar(libro_v)
        c_repo.agregar(cliente_v)
        hace_15 = date.today() - timedelta(days=15)
        ayer = date.today() - timedelta(days=1)
        p_vencido = Prestamo(p_repo.nuevo_id(), libro_v, cliente_v,
                             hace_15, ayer)
        libro_v.marcar_prestado()
        p_repo.agregar(p_vencido)

        return bsvc, psvc, p_activo, p_vencido

    def test_solo_prestamo_vencido_aparece_en_listado(self, sistema_con_vencidos):
        _, psvc, p_activo, p_vencido = sistema_con_vencidos
        vencidos = psvc.obtener_vencidos()
        assert p_vencido in vencidos
        assert p_activo not in vencidos

    def test_vencido_desaparece_tras_devolucion(self, sistema_con_vencidos):
        _, psvc, _, p_vencido = sistema_con_vencidos
        psvc.devolver_libro(p_vencido.id)
        assert psvc.obtener_vencidos() == []

    def test_libro_vuelve_a_estar_disponible_tras_devolucion_vencido(
        self, sistema_con_vencidos
    ):
        bsvc, psvc, _, p_vencido = sistema_con_vencidos
        psvc.devolver_libro(p_vencido.id)
        assert bsvc.obtener_libro("ISBN-VEN").esta_disponible() is True

    def test_estado_prestamo_vencido_es_vencido(self, sistema_con_vencidos):
        _, _, _, p_vencido = sistema_con_vencidos
        assert p_vencido.estado() == EstadoPrestamo.VENCIDO
        assert p_vencido.dias_vencido() >= 1

    def test_estado_prestamo_activo_no_es_vencido(self, sistema_con_vencidos):
        _, _, p_activo, _ = sistema_con_vencidos
        assert p_activo.estado() == EstadoPrestamo.ACTIVO
        assert p_activo.esta_vencido() is False


# ── E2E-06: Cliente con múltiples libros prestados simultáneamente ────────────

class TestE2E06ClienteConMultiplesLibros:
    """
    Escenario: un cliente pide dos libros en momentos distintos, los tiene
    prestados simultáneamente, devuelve uno y luego el otro. El sistema
    refleja el estado correcto en cada paso.
    """

    def test_flujo_cliente_con_dos_libros(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Libro Uno", "Ed", "A", "B")
        bsvc.agregar_libro("ISBN-002", "Libro Dos", "Ed", "A", "B")
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")

        # Paso 1: pedir los dos libros
        p1 = psvc.prestar_libro("ISBN-001", "12345678")
        p2 = psvc.prestar_libro("ISBN-002", "12345678")

        # Paso 2: ambos activos, ningún libro disponible
        activos = bsvc.obtener_prestamos_activos_de_cliente("12345678")
        assert len(activos) == 2
        assert bsvc.obtener_libros_disponibles() == []

        # Paso 3: devolver el primero
        psvc.devolver_libro(p1.id)
        activos = bsvc.obtener_prestamos_activos_de_cliente("12345678")
        assert len(activos) == 1
        assert p2 in activos
        assert bsvc.obtener_libro("ISBN-001").esta_disponible() is True
        assert bsvc.obtener_libro("ISBN-002").esta_disponible() is False

        # Paso 4: devolver el segundo
        psvc.devolver_libro(p2.id)
        assert bsvc.obtener_prestamos_activos_de_cliente("12345678") == []
        assert len(bsvc.obtener_libros_disponibles()) == 2

        # Paso 5: el historial completo tiene los dos préstamos
        historial = psvc.obtener_prestamos_de_cliente("12345678")
        assert len(historial) == 2
        assert all(p.esta_devuelto() for p in historial)


# ── E2E-07: Integridad ante registros duplicados ──────────────────────────────

class TestE2E07Duplicados:
    """
    Escenario: el bibliotecario intenta registrar por error entidades que
    ya existen. El sistema rechaza cada intento y conserva los datos
    originales intactos.
    """

    def test_autor_duplicado_es_rechazado(self, sistema):
        bsvc, *_ = sistema
        bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
        with pytest.raises(AutorYaExisteError):
            bsvc.agregar_autor("Gabriel", "García Márquez", "Otra")
        assert len(bsvc.obtener_autores()) == 1
        assert bsvc.buscar_autor("Gabriel", "García Márquez").nacionalidad == "Colombiana"

    def test_libro_isbn_duplicado_es_rechazado(self, sistema):
        bsvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Original", "Ed", "A", "B")
        with pytest.raises(LibroYaExisteError):
            bsvc.agregar_libro("ISBN-001", "Duplicado", "Ed", "A", "B")
        assert len(bsvc.obtener_libros()) == 1
        assert bsvc.obtener_libro("ISBN-001").titulo == "Original"

    def test_cliente_dni_duplicado_es_rechazado(self, sistema):
        bsvc, *_ = sistema
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")
        with pytest.raises(ClienteYaExisteError):
            bsvc.agregar_cliente("12345678", "Otro", "Nombre")
        assert len(bsvc.obtener_clientes()) == 1
        assert bsvc.obtener_cliente("12345678").nombre == "Juan"

    def test_prestamo_duplicado_es_rechazado(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(LibroNoDisponibleError):
            psvc.prestar_libro("ISBN-001", "12345678")
        assert len(psvc.obtener_prestamos()) == 1


# ── E2E-08: Baja de libro bloqueada → devolver → dar de baja ─────────────────

class TestE2E08BajaLibroConPrestamo:
    """
    Escenario: el bibliotecario intenta dar de baja un libro prestado.
    El sistema lo rechaza hasta que el libro es devuelto.
    """

    def test_flujo_completo_baja_libro(self, sistema):
        bsvc, psvc, *_ = sistema
        bsvc.agregar_autor("A", "B")
        bsvc.agregar_libro("ISBN-001", "Título", "Ed", "A", "B")
        bsvc.agregar_cliente("12345678", "Juan", "Pérez")

        # Paso 1: prestar el libro
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        assert bsvc.obtener_libro("ISBN-001").estado == EstadoLibro.PRESTADO

        # Paso 2: intento de baja → rechazado
        with pytest.raises(LibroPrestadoError):
            bsvc.dar_de_baja_libro("ISBN-001")
        assert bsvc.obtener_libro("ISBN-001") is not None

        # Paso 3: devolver el libro
        psvc.devolver_libro(prestamo.id)

        # Paso 4: ahora la baja procede
        bsvc.dar_de_baja_libro("ISBN-001")
        assert bsvc.obtener_libro("ISBN-001") is None
        assert bsvc.obtener_libros() == []


# ── E2E-09: Sistema vacío responde correctamente ──────────────────────────────

class TestE2E09SistemaVacio:
    """
    Escenario: el sistema recién iniciado responde correctamente a todas
    las consultas sin lanzar excepciones ni retornar datos inválidos.
    """

    def test_todas_las_consultas_en_sistema_vacio(self, sistema):
        bsvc, psvc, *_ = sistema
        assert bsvc.obtener_autores() == []
        assert bsvc.obtener_libros() == []
        assert bsvc.obtener_libros_disponibles() == []
        assert bsvc.obtener_clientes() == []
        assert bsvc.obtener_clientes_activos() == []
        assert psvc.obtener_prestamos() == []
        assert psvc.obtener_prestamos_activos() == []
        assert psvc.obtener_vencidos() == []

    def test_busquedas_en_sistema_vacio_retornan_none_o_vacio(self, sistema):
        bsvc, psvc, *_ = sistema
        assert bsvc.buscar_autor("No", "Existe") is None
        assert bsvc.obtener_libro("ISBN-X") is None
        assert bsvc.obtener_cliente("99999999") is None
        assert psvc.obtener_prestamos_de_cliente("99999999") == []
