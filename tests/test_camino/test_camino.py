"""
Pruebas de Camino (Basis Path Testing)
=======================================
Objetivo: garantizar que cada camino de ejecución independiente de los
métodos más complejos del sistema sea ejercitado al menos una vez.

Metodología (McCabe):
  V(G) = E - N + 2P  (aristas - nodos + 2 × componentes conexos)
  Para código lineal con condiciones: V(G) = número de condiciones + 1

Métodos analizados y su complejidad ciclomática:

  1. PrestamoService.prestar_libro()       V(G) = 5  → 5 caminos
  2. PrestamoService.devolver_libro()      V(G) = 3  → 3 caminos
  3. BibliotecaService.dar_de_baja_libro() V(G) = 3  → 3 caminos
  4. BibliotecaService.dar_de_baja_cliente() V(G) = 3 → 3 caminos
  5. Prestamo.esta_vencido()               V(G) = 3  → 3 caminos
  6. Prestamo.estado()                     V(G) = 3  → 3 caminos
"""
import pytest
from datetime import date, timedelta

from src.models.autor import Autor
from src.models.libro import Libro
from src.models.cliente import Cliente
from src.models.prestamo import Prestamo, EstadoPrestamo
from src.repositories.autor_repository import AutorRepository
from src.repositories.libro_repository import LibroRepository
from src.repositories.cliente_repository import ClienteRepository
from src.repositories.prestamo_repository import PrestamoRepository
from src.services.biblioteca_service import BibliotecaService
from src.services.prestamo_service import PrestamoService
from src.exceptions import (
    LibroNoEncontradoError,
    LibroNoDisponibleError,
    LibroPrestadoError,
    ClienteNoEncontradoError,
    ClienteInactivoError,
    PrestamoNoEncontradoError,
    PrestamoYaDevueltoError,
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
def sistema(servicios):
    bsvc, psvc = servicios
    bsvc.agregar_autor("Gabriel", "García Márquez", "Colombiana")
    bsvc.agregar_libro("ISBN-001", "Cien años de soledad", "Sudamericana",
                       "Gabriel", "García Márquez")
    bsvc.agregar_cliente("12345678", "Juan", "Pérez")
    return bsvc, psvc


# ─────────────────────────────────────────────────────────────────────────────
# 1. PrestamoService.prestar_libro()
#
# Grafo de flujo:
#   [inicio] → libro = repo.obtener(isbn)
#   → ¿libro is None?  SÍ → raise LibroNoEncontradoError      (Camino 1)
#                      NO → ¿not libro.esta_disponible()?
#                              SÍ → raise LibroNoDisponibleError (Camino 2)
#                              NO → cliente = repo.obtener(dni)
#                                   → ¿cliente is None?
#                                       SÍ → raise ClienteNoEncontrado (Camino 3)
#                                       NO → ¿not cliente.activo?
#                                               SÍ → raise ClienteInactivo (Camino 4)
#                                               NO → crear y retornar Prestamo (Camino 5)
#
# V(G) = 4 condiciones + 1 = 5
# ─────────────────────────────────────────────────────────────────────────────

class TestCaminoPrestarLibro:
    def test_camino_1_libro_no_encontrado(self, servicios):
        """Camino 1: libro is None → LibroNoEncontradoError"""
        _, psvc = servicios
        with pytest.raises(LibroNoEncontradoError):
            psvc.prestar_libro("ISBN-NO-EXISTE", "12345678")

    def test_camino_2_libro_no_disponible(self, sistema):
        """Camino 2: libro existe pero está prestado → LibroNoDisponibleError"""
        bsvc, psvc = sistema
        psvc.prestar_libro("ISBN-001", "12345678")
        bsvc.agregar_cliente("87654321", "Otro", "Cliente")
        with pytest.raises(LibroNoDisponibleError):
            psvc.prestar_libro("ISBN-001", "87654321")

    def test_camino_3_cliente_no_encontrado(self, sistema):
        """Camino 3: libro disponible, cliente is None → ClienteNoEncontradoError"""
        _, psvc = sistema
        with pytest.raises(ClienteNoEncontradoError):
            psvc.prestar_libro("ISBN-001", "DNI-NO-EXISTE")

    def test_camino_4_cliente_inactivo(self, sistema):
        """Camino 4: libro disponible, cliente inactivo → ClienteInactivoError"""
        bsvc, psvc = sistema
        bsvc.dar_de_baja_cliente("12345678")
        with pytest.raises(ClienteInactivoError):
            psvc.prestar_libro("ISBN-001", "12345678")

    def test_camino_5_prestamo_exitoso(self, sistema):
        """Camino 5: libro disponible + cliente activo → Prestamo creado"""
        _, psvc = sistema
        prestamo = psvc.prestar_libro("ISBN-001", "12345678", dias=14)
        assert prestamo.id == "P0001"
        assert prestamo.fecha_devolucion_esperada == date.today() + timedelta(days=14)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PrestamoService.devolver_libro()
#
# Grafo de flujo:
#   [inicio] → prestamo = repo.obtener(id)
#   → ¿prestamo is None? SÍ → raise PrestamoNoEncontrado     (Camino 1)
#                        NO → ¿prestamo.esta_devuelto()?
#                               SÍ → raise PrestamoYaDevuelto (Camino 2)
#                               NO → registrar devolución     (Camino 3)
#
# V(G) = 2 condiciones + 1 = 3
# ─────────────────────────────────────────────────────────────────────────────

class TestCaminoDevolverLibro:
    def test_camino_1_prestamo_no_encontrado(self, servicios):
        """Camino 1: préstamo no existe → PrestamoNoEncontradoError"""
        _, psvc = servicios
        with pytest.raises(PrestamoNoEncontradoError):
            psvc.devolver_libro("P9999")

    def test_camino_2_prestamo_ya_devuelto(self, sistema):
        """Camino 2: préstamo ya fue devuelto → PrestamoYaDevueltoError"""
        _, psvc = sistema
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        psvc.devolver_libro(prestamo.id)
        with pytest.raises(PrestamoYaDevueltoError):
            psvc.devolver_libro(prestamo.id)

    def test_camino_3_devolucion_exitosa(self, sistema):
        """Camino 3: préstamo activo → devolución registrada"""
        _, psvc = sistema
        prestamo = psvc.prestar_libro("ISBN-001", "12345678")
        devuelto = psvc.devolver_libro(prestamo.id)
        assert devuelto.esta_devuelto() is True
        assert devuelto.fecha_devolucion_real == date.today()
        assert devuelto.libro.esta_disponible() is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. BibliotecaService.dar_de_baja_libro()
#
# Grafo de flujo:
#   [inicio] → libro = repo.obtener(isbn)
#   → ¿libro is None? SÍ → raise LibroNoEncontrado           (Camino 1)
#                     NO → ¿not libro.esta_disponible()?
#                            SÍ → raise LibroPrestado         (Camino 2)
#                            NO → repo.eliminar(isbn)         (Camino 3)
#
# V(G) = 2 condiciones + 1 = 3
# ─────────────────────────────────────────────────────────────────────────────

class TestCaminoDarDeBajaLibro:
    def test_camino_1_libro_no_encontrado(self, servicios):
        """Camino 1: libro no existe → LibroNoEncontradoError"""
        bsvc, _ = servicios
        with pytest.raises(LibroNoEncontradoError):
            bsvc.dar_de_baja_libro("ISBN-NO-EXISTE")

    def test_camino_2_libro_esta_prestado(self, sistema):
        """Camino 2: libro prestado → LibroPrestadoError"""
        bsvc, psvc = sistema
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(LibroPrestadoError):
            bsvc.dar_de_baja_libro("ISBN-001")

    def test_camino_3_baja_exitosa(self, sistema):
        """Camino 3: libro disponible → eliminado del repositorio"""
        bsvc, _ = sistema
        bsvc.dar_de_baja_libro("ISBN-001")
        assert bsvc.obtener_libro("ISBN-001") is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. BibliotecaService.dar_de_baja_cliente()
#
# Grafo de flujo:
#   [inicio] → cliente = repo.obtener(dni)
#   → ¿cliente is None?  SÍ → raise ClienteNoEncontrado      (Camino 1)
#                        NO → pendientes = [p for p ...]
#                             → ¿pendientes?
#                                 SÍ → raise ClienteInactivo  (Camino 2)
#                                 NO → cliente.dar_de_baja()  (Camino 3)
#
# V(G) = 2 condiciones + 1 = 3
# ─────────────────────────────────────────────────────────────────────────────

class TestCaminoDarDeBajaCliente:
    def test_camino_1_cliente_no_encontrado(self, servicios):
        """Camino 1: cliente no existe → ClienteNoEncontradoError"""
        bsvc, _ = servicios
        with pytest.raises(ClienteNoEncontradoError):
            bsvc.dar_de_baja_cliente("DNI-NO-EXISTE")

    def test_camino_2_cliente_con_prestamos_activos(self, sistema):
        """Camino 2: cliente tiene préstamos sin devolver → ClienteInactivoError"""
        bsvc, psvc = sistema
        psvc.prestar_libro("ISBN-001", "12345678")
        with pytest.raises(ClienteInactivoError):
            bsvc.dar_de_baja_cliente("12345678")

    def test_camino_3_baja_exitosa(self, sistema):
        """Camino 3: cliente sin préstamos activos → dado de baja"""
        bsvc, _ = sistema
        bsvc.dar_de_baja_cliente("12345678")
        cliente = bsvc.obtener_cliente("12345678")
        assert cliente.activo is False


# ─────────────────────────────────────────────────────────────────────────────
# 5. Prestamo.esta_vencido()
#
# Grafo de flujo:
#   [inicio] → ¿esta_devuelto()?
#   → SÍ → return False                                       (Camino 1)
#   → NO → ¿date.today() > fecha_devolucion_esperada?
#           SÍ → return True                                  (Camino 2)
#           NO → return False                                 (Camino 3)
#
# V(G) = 2 condiciones + 1 = 3
# ─────────────────────────────────────────────────────────────────────────────

class TestCaminoEstaVencido:
    def _base(self, dias_hasta_vencimiento: int, devuelto: bool = False) -> Prestamo:
        autor = Autor("A", "B")
        libro = Libro("ISBN-X", "Título", "Ed", autor)
        cliente = Cliente("11111111", "Test", "User")
        hoy = date.today()
        p = Prestamo(
            id="P0001",
            libro=libro,
            cliente=cliente,
            fecha_prestamo=hoy - timedelta(days=20),
            fecha_devolucion_esperada=hoy + timedelta(days=dias_hasta_vencimiento),
        )
        if devuelto:
            p.fecha_devolucion_real = hoy
        return p

    def test_camino_1_devuelto_no_es_vencido(self):
        """Camino 1: esta_devuelto() == True → False"""
        p = self._base(dias_hasta_vencimiento=-5, devuelto=True)
        assert p.esta_vencido() is False

    def test_camino_2_no_devuelto_y_fecha_superada(self):
        """Camino 2: no devuelto + hoy > esperada → True"""
        p = self._base(dias_hasta_vencimiento=-1)
        assert p.esta_vencido() is True

    def test_camino_3_no_devuelto_y_dentro_del_plazo(self):
        """Camino 3: no devuelto + hoy <= esperada → False"""
        p = self._base(dias_hasta_vencimiento=7)
        assert p.esta_vencido() is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. Prestamo.estado()
#
# Grafo de flujo:
#   [inicio] → ¿esta_devuelto()?
#   → SÍ → return DEVUELTO                                    (Camino 1)
#   → NO → ¿esta_vencido()?
#           SÍ → return VENCIDO                               (Camino 2)
#           NO → return ACTIVO                                (Camino 3)
#
# V(G) = 2 condiciones + 1 = 3
# ─────────────────────────────────────────────────────────────────────────────

class TestCaminoEstado:
    def _base_prestamo(self, dias_hasta_vencimiento: int) -> Prestamo:
        autor = Autor("A", "B")
        libro = Libro("ISBN-X", "Título", "Ed", autor)
        cliente = Cliente("11111111", "Test", "User")
        hoy = date.today()
        return Prestamo(
            id="P0001",
            libro=libro,
            cliente=cliente,
            fecha_prestamo=hoy - timedelta(days=20),
            fecha_devolucion_esperada=hoy + timedelta(days=dias_hasta_vencimiento),
        )

    def test_camino_1_estado_devuelto(self):
        """Camino 1: esta_devuelto() == True → DEVUELTO"""
        p = self._base_prestamo(dias_hasta_vencimiento=7)
        p.fecha_devolucion_real = date.today()
        assert p.estado() == EstadoPrestamo.DEVUELTO

    def test_camino_2_estado_vencido(self):
        """Camino 2: no devuelto + esta_vencido() == True → VENCIDO"""
        p = self._base_prestamo(dias_hasta_vencimiento=-1)
        assert p.estado() == EstadoPrestamo.VENCIDO

    def test_camino_3_estado_activo(self):
        """Camino 3: no devuelto + no vencido → ACTIVO"""
        p = self._base_prestamo(dias_hasta_vencimiento=7)
        assert p.estado() == EstadoPrestamo.ACTIVO
