"""
Pruebas de Componentes
======================
Objetivo: verificar el comportamiento de cada clase y método de forma
aislada, sin interacción entre módulos. Cada test ejerce una única
responsabilidad.
"""
import pytest
from datetime import date, timedelta

from src.models.autor import Autor
from src.models.libro import Libro, EstadoLibro
from src.models.cliente import Cliente
from src.models.prestamo import Prestamo, EstadoPrestamo
from src.repositories.autor_repository import AutorRepository
from src.repositories.libro_repository import LibroRepository
from src.repositories.cliente_repository import ClienteRepository
from src.repositories.prestamo_repository import PrestamoRepository
from src.exceptions import (
    AutorYaExisteError, AutorNoEncontradoError,
    LibroYaExisteError, LibroNoEncontradoError,
    ClienteYaExisteError,
)


# ── Fixtures locales ──────────────────────────────────────────────────────────

@pytest.fixture
def autor_simple():
    return Autor("Gabriel", "García Márquez", "Colombiana")


@pytest.fixture
def libro_simple(autor_simple):
    return Libro("ISBN-001", "Cien años de soledad", "Sudamericana", autor_simple)


@pytest.fixture
def cliente_simple():
    return Cliente("12345678", "Juan", "Pérez")


@pytest.fixture
def prestamo_activo(libro_simple, cliente_simple):
    hoy = date.today()
    return Prestamo(
        id="P0001",
        libro=libro_simple,
        cliente=cliente_simple,
        fecha_prestamo=hoy,
        fecha_devolucion_esperada=hoy + timedelta(days=14),
    )


@pytest.fixture
def prestamo_vencido(autor_simple):
    libro = Libro("ISBN-VEN", "Libro Vencido", "Ed", autor_simple)
    cliente = Cliente("99999999", "Pedro", "Vencido")
    hace_20 = date.today() - timedelta(days=20)
    ayer = date.today() - timedelta(days=1)
    return Prestamo("P0002", libro, cliente, hace_20, ayer)


@pytest.fixture
def prestamo_devuelto(libro_simple, cliente_simple):
    hoy = date.today()
    p = Prestamo(
        id="P0003",
        libro=libro_simple,
        cliente=cliente_simple,
        fecha_prestamo=hoy - timedelta(days=5),
        fecha_devolucion_esperada=hoy + timedelta(days=9),
    )
    p.fecha_devolucion_real = hoy
    return p


# ── Componente: Autor ─────────────────────────────────────────────────────────

class TestComponenteAutor:
    def test_nombre_completo_combina_nombre_y_apellido(self, autor_simple):
        assert autor_simple.nombre_completo() == "Gabriel García Márquez"

    def test_nombre_se_normaliza_con_strip(self):
        a = Autor("  Ana  ", "  García  ")
        assert a.nombre == "Ana"
        assert a.apellido == "García"

    def test_nacionalidad_se_normaliza_con_strip(self):
        a = Autor("Ana", "García", "  Argentina  ")
        assert a.nacionalidad == "Argentina"

    def test_nacionalidad_vacia_por_defecto(self):
        a = Autor("Ana", "García")
        assert a.nacionalidad == ""

    def test_nombre_vacio_lanza_valueerror(self):
        with pytest.raises(ValueError, match="nombre"):
            Autor("", "García")

    def test_nombre_solo_espacios_lanza_valueerror(self):
        with pytest.raises(ValueError, match="nombre"):
            Autor("   ", "García")

    def test_apellido_vacio_lanza_valueerror(self):
        with pytest.raises(ValueError, match="apellido"):
            Autor("Ana", "")

    def test_igualdad_case_insensitive(self):
        a1 = Autor("gabriel", "garcía márquez")
        a2 = Autor("GABRIEL", "GARCÍA MÁRQUEZ")
        assert a1 == a2

    def test_distintos_nombres_no_son_iguales(self):
        a1 = Autor("Gabriel", "García Márquez")
        a2 = Autor("Jorge", "Borges")
        assert a1 != a2

    def test_hash_igual_para_autores_equivalentes(self):
        a1 = Autor("juan", "pérez")
        a2 = Autor("JUAN", "PÉREZ")
        assert hash(a1) == hash(a2)

    def test_no_es_igual_a_tipo_distinto(self, autor_simple):
        assert autor_simple != "Gabriel García Márquez"
        assert autor_simple != 42


# ── Componente: Libro ─────────────────────────────────────────────────────────

class TestComponenteLibro:
    def test_estado_inicial_es_disponible(self, libro_simple):
        assert libro_simple.estado == EstadoLibro.DISPONIBLE

    def test_esta_disponible_retorna_true_al_inicio(self, libro_simple):
        assert libro_simple.esta_disponible() is True

    def test_marcar_prestado_cambia_estado(self, libro_simple):
        libro_simple.marcar_prestado()
        assert libro_simple.estado == EstadoLibro.PRESTADO
        assert libro_simple.esta_disponible() is False

    def test_marcar_disponible_restaura_estado(self, libro_simple):
        libro_simple.marcar_prestado()
        libro_simple.marcar_disponible()
        assert libro_simple.esta_disponible() is True

    def test_doble_marcar_prestado_no_lanza_error(self, libro_simple):
        libro_simple.marcar_prestado()
        libro_simple.marcar_prestado()
        assert libro_simple.estado == EstadoLibro.PRESTADO

    def test_isbn_se_normaliza_con_strip(self, autor_simple):
        libro = Libro("  ISBN-X  ", "Título", "Editorial", autor_simple)
        assert libro.isbn == "ISBN-X"

    def test_isbn_vacio_lanza_valueerror(self, autor_simple):
        with pytest.raises(ValueError, match="ISBN"):
            Libro("", "Título", "Editorial", autor_simple)

    def test_titulo_vacio_lanza_valueerror(self, autor_simple):
        with pytest.raises(ValueError, match="título"):
            Libro("ISBN-1", "", "Editorial", autor_simple)

    def test_editorial_vacia_lanza_valueerror(self, autor_simple):
        with pytest.raises(ValueError, match="editorial"):
            Libro("ISBN-1", "Título", "", autor_simple)

    def test_igualdad_basada_en_isbn(self, autor_simple):
        l1 = Libro("ISBN-1", "Nombre A", "Ed A", autor_simple)
        l2 = Libro("ISBN-1", "Nombre B", "Ed B", autor_simple)
        assert l1 == l2

    def test_distintos_isbn_no_son_iguales(self, autor_simple):
        l1 = Libro("ISBN-1", "Título", "Ed", autor_simple)
        l2 = Libro("ISBN-2", "Título", "Ed", autor_simple)
        assert l1 != l2

    def test_no_es_igual_a_tipo_distinto(self, libro_simple):
        assert libro_simple != "ISBN-001"


# ── Componente: Cliente ───────────────────────────────────────────────────────

class TestComponenteCliente:
    def test_activo_por_defecto(self, cliente_simple):
        assert cliente_simple.activo is True

    def test_dar_de_baja_desactiva_cliente(self, cliente_simple):
        cliente_simple.dar_de_baja()
        assert cliente_simple.activo is False

    def test_nombre_completo_combina_nombre_y_apellido(self, cliente_simple):
        assert cliente_simple.nombre_completo() == "Juan Pérez"

    def test_dni_se_normaliza_con_strip(self):
        c = Cliente("  12345678  ", "Juan", "Pérez")
        assert c.dni == "12345678"

    def test_dni_vacio_lanza_valueerror(self):
        with pytest.raises(ValueError, match="DNI"):
            Cliente("", "Juan", "Pérez")

    def test_nombre_vacio_lanza_valueerror(self):
        with pytest.raises(ValueError, match="nombre"):
            Cliente("12345678", "", "Pérez")

    def test_apellido_vacio_lanza_valueerror(self):
        with pytest.raises(ValueError, match="apellido"):
            Cliente("12345678", "Juan", "")

    def test_igualdad_basada_en_dni(self):
        c1 = Cliente("12345678", "Juan", "Pérez")
        c2 = Cliente("12345678", "Otro", "Nombre")
        assert c1 == c2

    def test_distintos_dni_no_son_iguales(self):
        c1 = Cliente("11111111", "Juan", "Pérez")
        c2 = Cliente("22222222", "Juan", "Pérez")
        assert c1 != c2


# ── Componente: Prestamo ──────────────────────────────────────────────────────

class TestComponentePrestamo:
    def test_no_devuelto_al_crearse(self, prestamo_activo):
        assert prestamo_activo.esta_devuelto() is False

    def test_devuelto_cuando_tiene_fecha_real(self, prestamo_devuelto):
        assert prestamo_devuelto.esta_devuelto() is True

    def test_no_vencido_si_dentro_del_plazo(self, prestamo_activo):
        assert prestamo_activo.esta_vencido() is False

    def test_vencido_si_fecha_limite_superada(self, prestamo_vencido):
        assert prestamo_vencido.esta_vencido() is True

    def test_devuelto_nunca_es_vencido(self, prestamo_devuelto):
        assert prestamo_devuelto.esta_vencido() is False

    def test_estado_activo(self, prestamo_activo):
        assert prestamo_activo.estado() == EstadoPrestamo.ACTIVO

    def test_estado_vencido(self, prestamo_vencido):
        assert prestamo_vencido.estado() == EstadoPrestamo.VENCIDO

    def test_estado_devuelto(self, prestamo_devuelto):
        assert prestamo_devuelto.estado() == EstadoPrestamo.DEVUELTO

    def test_dias_vencido_es_cero_si_no_vencido(self, prestamo_activo):
        assert prestamo_activo.dias_vencido() == 0

    def test_dias_vencido_es_positivo_si_vencido(self, prestamo_vencido):
        assert prestamo_vencido.dias_vencido() >= 1

    def test_fecha_devolucion_igual_a_prestamo_lanza_error(self, autor_simple):
        libro = Libro("ISBN-X", "X", "E", autor_simple)
        cliente = Cliente("11111111", "X", "Y")
        hoy = date.today()
        with pytest.raises(ValueError):
            Prestamo("P9999", libro, cliente, hoy, hoy)

    def test_fecha_devolucion_anterior_a_prestamo_lanza_error(self, autor_simple):
        libro = Libro("ISBN-X", "X", "E", autor_simple)
        cliente = Cliente("11111111", "X", "Y")
        hoy = date.today()
        with pytest.raises(ValueError):
            Prestamo("P9999", libro, cliente, hoy, hoy - timedelta(days=1))


# ── Componente: AutorRepository ───────────────────────────────────────────────

class TestComponenteAutorRepository:
    def test_agregar_y_buscar_autor(self, autor_simple):
        repo = AutorRepository()
        repo.agregar(autor_simple)
        assert repo.buscar("Gabriel", "García Márquez") == autor_simple

    def test_buscar_inexistente_retorna_none(self):
        repo = AutorRepository()
        assert repo.buscar("No", "Existe") is None

    def test_agregar_duplicado_lanza_error(self, autor_simple):
        repo = AutorRepository()
        repo.agregar(autor_simple)
        with pytest.raises(AutorYaExisteError):
            repo.agregar(Autor("Gabriel", "García Márquez"))

    def test_eliminar_autor_existente(self, autor_simple):
        repo = AutorRepository()
        repo.agregar(autor_simple)
        repo.eliminar("Gabriel", "García Márquez")
        assert repo.buscar("Gabriel", "García Márquez") is None

    def test_eliminar_inexistente_lanza_error(self):
        repo = AutorRepository()
        with pytest.raises(AutorNoEncontradoError):
            repo.eliminar("No", "Existe")

    def test_existe_retorna_true_tras_agregar(self, autor_simple):
        repo = AutorRepository()
        repo.agregar(autor_simple)
        assert repo.existe("Gabriel", "García Márquez") is True

    def test_existe_retorna_false_si_no_agregado(self):
        repo = AutorRepository()
        assert repo.existe("No", "Existe") is False

    def test_cantidad_refleja_total_de_autores(self):
        repo = AutorRepository()
        assert repo.cantidad() == 0
        repo.agregar(Autor("A", "B"))
        repo.agregar(Autor("C", "D"))
        assert repo.cantidad() == 2

    def test_obtener_todos_retorna_todos_los_autores(self):
        repo = AutorRepository()
        a1 = Autor("A", "B")
        a2 = Autor("C", "D")
        repo.agregar(a1)
        repo.agregar(a2)
        todos = repo.obtener_todos()
        assert a1 in todos and a2 in todos


# ── Componente: LibroRepository ───────────────────────────────────────────────

class TestComponenteLibroRepository:
    def test_agregar_y_obtener_por_isbn(self, libro_simple):
        repo = LibroRepository()
        repo.agregar(libro_simple)
        assert repo.obtener_por_isbn("ISBN-001") == libro_simple

    def test_obtener_isbn_inexistente_retorna_none(self):
        repo = LibroRepository()
        assert repo.obtener_por_isbn("ISBN-X") is None

    def test_agregar_isbn_duplicado_lanza_error(self, libro_simple):
        repo = LibroRepository()
        repo.agregar(libro_simple)
        with pytest.raises(LibroYaExisteError):
            repo.agregar(libro_simple)

    def test_obtener_disponibles_excluye_prestados(self, libro_simple):
        repo = LibroRepository()
        repo.agregar(libro_simple)
        libro_simple.marcar_prestado()
        assert repo.obtener_disponibles() == []

    def test_eliminar_libro_existente(self, libro_simple):
        repo = LibroRepository()
        repo.agregar(libro_simple)
        repo.eliminar("ISBN-001")
        assert repo.obtener_por_isbn("ISBN-001") is None

    def test_eliminar_isbn_inexistente_lanza_error(self):
        repo = LibroRepository()
        with pytest.raises(LibroNoEncontradoError):
            repo.eliminar("ISBN-NO-EXISTE")


# ── Componente: ClienteRepository ─────────────────────────────────────────────

class TestComponenteClienteRepository:
    def test_agregar_y_obtener_por_dni(self, cliente_simple):
        repo = ClienteRepository()
        repo.agregar(cliente_simple)
        assert repo.obtener_por_dni("12345678") == cliente_simple

    def test_obtener_dni_inexistente_retorna_none(self):
        repo = ClienteRepository()
        assert repo.obtener_por_dni("99999999") is None

    def test_agregar_dni_duplicado_lanza_error(self, cliente_simple):
        repo = ClienteRepository()
        repo.agregar(cliente_simple)
        with pytest.raises(ClienteYaExisteError):
            repo.agregar(Cliente("12345678", "Otro", "Nombre"))

    def test_obtener_activos_excluye_dados_de_baja(self, cliente_simple):
        repo = ClienteRepository()
        repo.agregar(cliente_simple)
        cliente_simple.dar_de_baja()
        assert repo.obtener_activos() == []


# ── Componente: PrestamoRepository ────────────────────────────────────────────

class TestComponentePrestamoRepository:
    def test_nuevo_id_es_secuencial(self):
        repo = PrestamoRepository()
        assert repo.nuevo_id() == "P0001"
        assert repo.nuevo_id() == "P0002"
        assert repo.nuevo_id() == "P0003"

    def test_agregar_y_obtener_por_id(self, prestamo_activo):
        repo = PrestamoRepository()
        repo.agregar(prestamo_activo)
        assert repo.obtener_por_id("P0001") == prestamo_activo

    def test_obtener_id_inexistente_retorna_none(self):
        repo = PrestamoRepository()
        assert repo.obtener_por_id("P9999") is None

    def test_obtener_activos_excluye_devueltos(self, prestamo_activo, prestamo_devuelto):
        repo = PrestamoRepository()
        repo.agregar(prestamo_activo)
        repo.agregar(prestamo_devuelto)
        activos = repo.obtener_activos()
        assert prestamo_activo in activos
        assert prestamo_devuelto not in activos

    def test_obtener_por_cliente_filtra_por_dni(self, prestamo_activo):
        repo = PrestamoRepository()
        repo.agregar(prestamo_activo)
        resultado = repo.obtener_por_cliente("12345678")
        assert prestamo_activo in resultado

    def test_obtener_por_cliente_sin_prestamos_retorna_lista_vacia(self):
        repo = PrestamoRepository()
        assert repo.obtener_por_cliente("00000000") == []

    def test_cantidad_refleja_total(self, prestamo_activo):
        repo = PrestamoRepository()
        assert repo.cantidad() == 0
        repo.agregar(prestamo_activo)
        assert repo.cantidad() == 1
