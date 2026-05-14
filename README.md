# TP_Final_Testing
Trabajo Practico Final Testing

GRAFICOS UML:
El sistema sigue el patrón de **arquitectura en capas**:

```
┌──────────────────────────────────┐
│           GUI (tkinter)           │  ← Presentación
│  Autores │ Libros │ Clientes     │
│  Préstamos │ Vencidos            │
├──────────────────────────────────┤
│         Capa de Servicios         │  ← Lógica de negocio
│  BibliotecaService               │
│  PrestamoService                 │
├──────────────────────────────────┤
│        Capa de Repositorios       │  ← Acceso a datos
│  AutorRepo │ LibroRepo           │
│  ClienteRepo │ PrestamoRepo      │
├──────────────────────────────────┤
│           Modelos                 │  ← Entidades del dominio
│  Autor │ Libro │ Cliente         │
│  Prestamo                        │
└──────────────────────────────────┘
           (todo en memoria)
```

---

## 6. Suite de Tests

El proyecto cuenta con **146 tests automatizados** organizados en tres niveles:

| Nivel | Archivos | Tests | Descripción |
|-------|----------|-------|-------------|
| Modelos | 4 archivos | 52 tests | Validación de creación, estados y reglas de negocio de cada entidad |
| Repositorios | 4 archivos | 50 tests | Operaciones CRUD, filtros y manejo de errores en cada repositorio |
| Servicios | 2 archivos | 44 tests | Casos de uso completos, incluyendo caminos felices y casos de error |

**Herramienta:** `pytest 9.0.3`  
**Comando:** `py -m pytest`

---

## 7. Cómo Ejecutar

**Aplicación gráfica:**
```
py main.py
```

**Tests:**
```
py -m pytest
py -m pytest --cov=src --cov-report=term-missing
```

**Ejecutable (sin Python instalado):**
```
dist/BibliotecaBarrial.exe
```
