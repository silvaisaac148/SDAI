# Contribuir a SDAI

Proyecto académico mantenido por Isaac Silva, Carlos Herrera y Ángel Ramos. Pull requests externos son bienvenidos siempre que respeten los siguientes lineamientos.

---

## Setup de desarrollo

```bash
git clone <repo>
cd proyecto_franklin
python -m venv .venv
.venv\Scripts\activate                 # o source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# rellenar SUPABASE_URL + SUPABASE_KEY como mínimo
python scripts/verify_schema.py        # confirma schema OK
pytest tests/                          # 58 tests deben pasar antes de tocar nada
```

---

## Flujo de un cambio

1. Crear branch desde `main`: `git checkout -b feat/nombre-corto`
2. Implementar el cambio + tests
3. `pytest tests/` debe pasar localmente
4. Commit con mensaje convencional (ver abajo)
5. Pull request a `main` con descripción, motivación y screenshots si toca UI

---

## Convenciones de commit

Conventional Commits sin scope obligatorio:

- `feat: añadir detector dns-tunneling`
- `fix: brute_force ignoraba flags PA en TCP`
- `refactor: extraer query builder en events.py`
- `docs: actualizar README sección instalación`
- `test: cobertura para investigate endpoint`
- `chore: bump requirements supabase a 2.10`

Cuerpo opcional explica el **porqué**, no el qué (el diff ya cuenta el qué).

---

## Estilo de código

- Python: PEP 8, líneas ≤120 chars. Type hints en funciones públicas.
- No introducir abstracciones especulativas. Tres llamadas similares > una abstracción prematura.
- Comentarios solo cuando el **porqué** no es obvio del código. Nada de "incrementa contador en 1".
- Tests: un módulo `test_X.py` por feature. Nombre descriptivo: `test_brute_force_ignores_tcp_non_syn`.

---

## Áreas con buena primera contribución

- Documentación de cada detector con ejemplos de tráfico real
- Tests adicionales sobre edge cases (paquetes malformados, IPv6, IPs en surrogate ranges)
- Templates HTML para emails (actualmente texto plano)
- Manual instalación PyME en español, paso a paso, capturas de pantalla
- Detector adicional: DNS tunneling, ARP spoof, beaconing C2

---

## Reportar bugs / proponer features

Issues en GitHub con plantilla:

- **Versión** (commit hash)
- **Pasos para reproducir** o caso de uso
- **Comportamiento observado** vs esperado
- **Entorno**: OS, Python, Npcap version si aplica

---

## Contacto

Equipo SDAI · proyecto académico Universidad / Estado Barinas, Venezuela.
