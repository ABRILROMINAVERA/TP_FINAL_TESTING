"""
Pruebas de Rendimiento
======================
Objetivo: verificar que el sistema cumple el Requerimiento No Funcional
RNF07 ("todas las operaciones deben tener tiempo de respuesta inmediato,
< 100 ms") bajo carga representativa.

Metodología:
  - Se mide con time.perf_counter() para máxima resolución.
  - Se prueba con volúmenes de 100, 500 y 1 000 registros.
  - El umbral máximo permitido por operación individual es 100 ms.
  - Las operaciones de carga masiva se validan contra un umbral
    proporcional (1 000 registros < 500 ms).
"""
import time
import pytest
from datetime import date, timedelta

from src.models.autor import Autor
from src.models.libro import Libro
from src.models.cliente import Cliente
from src.models.prestamo import Prestamo
from src.repositories.autor_repository import AutorRepository
from src.repositories.libro_repository import LibroRepository
from src.repositories.cliente_repository import ClienteRepository
from src.repositories.prestamo_repository import PrestamoRepository
from src.services.biblioteca_service import BibliotecaService
from src.services.prestamo_service import PrestamoService

LIMITE_OP_INDIVIDUAL_MS = 100
LIMITE_CARGA_MASIVA_MS  = 500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _crear_sistema_con_n_registros(n: int):
    a_repo = AutorRepository()
    l_repo = LibroRepository()
    c_repo = ClienteRepository()
    p_repo = PrestamoRepository()

    autor = Autor("Autor", "Unico")
    a_repo.agregar(autor)

    for i in range(n):
        libro = Libro(f"ISBN-{i:05d}", f"Título {i}", "Editorial", autor)
        l_repo.agregar(libro)
        cliente = Cliente(f"{i:08d}", f"Nombre{i}", f"Apellido{i}")
        c_repo.agregar(cliente)

    bsvc = BibliotecaService(a_repo, l_repo, c_repo, p_repo)
    psvc = PrestamoService(l_repo, c_repo, p_repo)
    return bsvc, psvc, l_repo, c_repo, p_repo


def _ms(inicio: float) -> float:
    return (time.perf_counter() - inicio) * 1000


# ── Rendimiento: operaciones individuales ─────────────────────────────────────

class TestRendimientoOperacionesIndividuales:
    def test_agregar_autor_es_menor_a_100ms(self):
        repo = AutorRepository()
        inicio = time.perf_counter()
        repo.agregar(Autor("Test", "Autor"))
        assert _ms(inicio) < LIMITE_OP_INDIVIDUAL_MS

    def test_agregar_libro_es_menor_a_100ms(self):
        autor = Autor("Test", "Autor")
        repo = LibroRepository()
        inicio = time.perf_counter()
        repo.agregar(Libro("ISBN-T", "Título", "Ed", autor))
        assert _ms(inicio) < LIMITE_OP_INDIVIDUAL_MS

    def test_agregar_cliente_es_menor_a_100ms(self):
        repo = ClienteRepository()
        inicio = time.perf_counter()
        repo.agregar(Cliente("12345678", "Juan", "Pérez"))
        assert _ms(inicio) < LIMITE_OP_INDIVIDUAL_MS

    def test_buscar_autor_es_menor_a_100ms(self):
        repo = AutorRepository()
        repo.agregar(Autor("Gabriel", "García Márquez"))
        inicio = time.perf_counter()
        repo.buscar("Gabriel", "García Márquez")
        assert _ms(inicio) < LIMITE_OP_INDIVIDUAL_MS

    def test_obtener_libro_por_isbn_es_menor_a_100ms(self):
        autor = Autor("A", "B")
        repo = LibroRepository()
        repo.agregar(Libro("ISBN-001", "Título", "Ed", autor))
        inicio = time.perf_counter()
        repo.obtener_por_isbn("ISBN-001")
        assert _ms(inicio) < LIMITE_OP_INDIVIDUAL_MS

    def test_prestar_libro_es_menor_a_100ms(self):
        bsvc, psvc, *_ = _crear_sistema_con_n_registros(1)
        inicio = time.perf_counter()
        psvc.prestar_libro("ISBN-00000", "00000000")
        assert _ms(inicio) < LIMITE_OP_INDIVIDUAL_MS

    def test_devolver_libro_es_menor_a_100ms(self):
        bsvc, psvc, *_ = _crear_sistema_con_n_registros(1)
        prestamo = psvc.prestar_libro("ISBN-00000", "00000000")
        inicio = time.perf_counter()
        psvc.devolver_libro(prestamo.id)
        assert _ms(inicio) < LIMITE_OP_INDIVIDUAL_MS


# ── Rendimiento: consultas con 500 registros ──────────────────────────────────

class TestRendimientoConsultasMedianas:
    @pytest.fixture(scope="class")
    def sistema_500(self):
        return _crear_sistema_con_n_registros(500)

    def test_obtener_todos_los_libros_500(self, sistema_500):
        bsvc, *_ = sistema_500
        inicio = time.perf_counter()
        libros = bsvc.obtener_libros()
        elapsed = _ms(inicio)
        assert len(libros) == 500
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_obtener_libros_disponibles_500(self, sistema_500):
        bsvc, *_ = sistema_500
        inicio = time.perf_counter()
        disponibles = bsvc.obtener_libros_disponibles()
        elapsed = _ms(inicio)
        assert len(disponibles) == 500
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_obtener_todos_los_clientes_500(self, sistema_500):
        bsvc, *_ = sistema_500
        inicio = time.perf_counter()
        clientes = bsvc.obtener_clientes()
        elapsed = _ms(inicio)
        assert len(clientes) == 500
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_obtener_clientes_activos_500(self, sistema_500):
        bsvc, *_ = sistema_500
        inicio = time.perf_counter()
        activos = bsvc.obtener_clientes_activos()
        elapsed = _ms(inicio)
        assert len(activos) == 500
        assert elapsed < LIMITE_CARGA_MASIVA_MS


# ── Rendimiento: carga masiva de 1 000 registros ─────────────────────────────

class TestRendimientoCargaMasiva:
    def test_insertar_1000_autores(self):
        repo = AutorRepository()
        inicio = time.perf_counter()
        for i in range(1000):
            repo.agregar(Autor(f"Nombre{i}", f"Apellido{i}"))
        elapsed = _ms(inicio)
        assert repo.cantidad() == 1000
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_insertar_1000_libros(self):
        autor = Autor("A", "B")
        repo = LibroRepository()
        inicio = time.perf_counter()
        for i in range(1000):
            repo.agregar(Libro(f"ISBN-{i:05d}", f"Título {i}", "Ed", autor))
        elapsed = _ms(inicio)
        assert repo.cantidad() == 1000
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_insertar_1000_clientes(self):
        repo = ClienteRepository()
        inicio = time.perf_counter()
        for i in range(1000):
            repo.agregar(Cliente(f"{i:08d}", f"Nombre{i}", f"Apellido{i}"))
        elapsed = _ms(inicio)
        assert repo.cantidad() == 1000
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_insertar_1000_prestamos(self):
        autor = Autor("A", "B")
        p_repo = PrestamoRepository()
        hoy = date.today()
        inicio = time.perf_counter()
        for i in range(1000):
            libro = Libro(f"ISBN-{i:05d}", f"Título {i}", "Ed", autor)
            cliente = Cliente(f"{i:08d}", f"Nombre{i}", f"Apellido{i}")
            prestamo = Prestamo(
                id=p_repo.nuevo_id(),
                libro=libro,
                cliente=cliente,
                fecha_prestamo=hoy,
                fecha_devolucion_esperada=hoy + timedelta(days=14),
            )
            p_repo.agregar(prestamo)
        elapsed = _ms(inicio)
        assert p_repo.cantidad() == 1000
        assert elapsed < LIMITE_CARGA_MASIVA_MS


# ── Rendimiento: filtros y búsquedas con 1 000 préstamos ─────────────────────

class TestRendimientoFiltros:
    @pytest.fixture(scope="class")
    def sistema_con_prestamos(self):
        autor = Autor("A", "B")
        a_repo = AutorRepository()
        l_repo = LibroRepository()
        c_repo = ClienteRepository()
        p_repo = PrestamoRepository()
        a_repo.agregar(autor)

        hoy = date.today()
        ayer = hoy - timedelta(days=1)
        hace_20 = hoy - timedelta(days=20)

        # 500 préstamos activos + 500 vencidos
        for i in range(500):
            libro = Libro(f"ISBN-A{i:04d}", f"Activo {i}", "Ed", autor)
            cliente = Cliente(f"A{i:07d}", f"N{i}", f"A{i}")
            l_repo.agregar(libro)
            c_repo.agregar(cliente)
            p = Prestamo(p_repo.nuevo_id(), libro, cliente, hoy,
                         hoy + timedelta(days=14))
            libro.marcar_prestado()
            p_repo.agregar(p)

        for i in range(500):
            libro = Libro(f"ISBN-V{i:04d}", f"Vencido {i}", "Ed", autor)
            cliente = Cliente(f"V{i:07d}", f"N{i}", f"A{i}")
            l_repo.agregar(libro)
            c_repo.agregar(cliente)
            p = Prestamo(p_repo.nuevo_id(), libro, cliente, hace_20, ayer)
            libro.marcar_prestado()
            p_repo.agregar(p)

        return PrestamoService(l_repo, c_repo, p_repo)

    def test_obtener_prestamos_activos_1000(self, sistema_con_prestamos):
        # obtener_activos() devuelve todos los no-devueltos (activos + vencidos)
        psvc = sistema_con_prestamos
        inicio = time.perf_counter()
        activos = psvc.obtener_prestamos_activos()
        elapsed = _ms(inicio)
        assert len(activos) == 1000
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_obtener_vencidos_1000(self, sistema_con_prestamos):
        psvc = sistema_con_prestamos
        inicio = time.perf_counter()
        vencidos = psvc.obtener_vencidos()
        elapsed = _ms(inicio)
        assert len(vencidos) == 500
        assert elapsed < LIMITE_CARGA_MASIVA_MS

    def test_obtener_todos_prestamos_1000(self, sistema_con_prestamos):
        psvc = sistema_con_prestamos
        inicio = time.perf_counter()
        todos = psvc.obtener_prestamos()
        elapsed = _ms(inicio)
        assert len(todos) == 1000
        assert elapsed < LIMITE_CARGA_MASIVA_MS
