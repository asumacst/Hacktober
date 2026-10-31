# ReciclaClaro

Fotografía tus residuos, confirma los materiales y recibe un plan para prepararlos y entregarlos en un centro de acopio de Panamá, con la regla, la fuente y la fecha de cada decisión.

Proyecto creado en Hacktoberfest Hack Day Panama City 2026 (31 de octubre de 2026). Licencia [MIT](LICENSE).

## Qué es y qué problema resuelve

Saber si algo "es reciclable" no basta: hay que saber cómo prepararlo y si el centro elegido lo recibe. ReciclaClaro usa Gemma 4 para proponer qué objetos y materiales hay en una foto; la persona confirma o corrige esa propuesta, y un comparador determinístico la contrasta con las condiciones documentadas del centro. La IA nunca decide si un centro acepta algo: eso sale del catálogo, y si falta evidencia el resultado queda como **pendiente de confirmar**.

**Flujo:** foto → identificación con Gemma 4 → confirmación humana → selección de centro → comparación determinística → plan con fuentes.

## Cómo usamos Gemma 4

| | |
| --- | --- |
| Modelo | `gemma-4-26b-a4b-it` (respaldo: `gemma-4-31b-it`) |
| Acceso | Gemini API, con el SDK `google-genai` |
| Dónde | `src/reciclaclaro/ai/` (capa de IA, en construcción), llamada por `src/reciclaclaro/orchestrator.py` |
| Qué hace | Propone objetos, materiales y preguntas pendientes a partir de la foto |
| Qué no hace | No decide aceptación, no inventa centros, reglas, fuentes ni fechas |

El motivo de la elección está en [docs/decisions.md](docs/decisions.md). La foto se envía a la Gemini API de Google para su análisis; no se guarda en el repositorio. El modo local con Ollama es opcional y no sustituye a la Gemini API.

> **Estado actual:** la llamada real a Gemma 4 todavía no está integrada. Mientras tanto el orquestador devuelve una respuesta de ejemplo marcada como **MOCK** (`is_mock=True`) y la interfaz lo indica en pantalla.

## Instalación y uso

Requiere Python 3.13 y una clave de la Gemini API ([Google AI Studio](https://aistudio.google.com/)).

```bash
git clone https://github.com/asumacst/Hacktober.git
cd Hacktober
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --prefer-binary -r requirements.txt
cp .env.example .env    # escribe tu GEMINI_API_KEY en .env
streamlit run src/reciclaclaro/ui/app.py
```

En Mac con procesador Intel, actualizar pip y usar `--prefer-binary` evita que `cryptography` intente compilarse.

**Pruebas** (sin red ni cuota de Gemini):

```bash
python -m pytest -q
```

**Ejemplos del comparador** (sintéticos, sin IA):

```bash
PYTHONPATH=src python -m reciclaclaro.logic.examples
```

## Arquitectura

| Capa | Carpeta | Responsabilidad |
| --- | --- | --- |
| Interfaz | `src/reciclaclaro/ui/` | Foto, revisión, correcciones, centro, plan y errores (Streamlit) |
| Orquestador | `src/reciclaclaro/orchestrator.py` | `identify`, `list_centers` y `compare`; valida entradas y convierte fallos en errores manejables |
| IA | `src/reciclaclaro/ai/` | Cliente de Gemma 4, prompt y validación de la respuesta |
| Lógica y datos | `src/reciclaclaro/logic/`, `data/` | Catálogo documentado y comparador determinístico |

Los datos que pasan entre capas están definidos en [`contracts.py`](src/reciclaclaro/contracts.py) y explicados en [docs/api-contract.md](docs/api-contract.md).

## Centro de acopio documentado

**CAR Ciudad del Saber**, operado por FAS Panamá. Reglas, fuentes y fechas de consulta en [`data/centers.json`](data/centers.json) y [`data/README.md`](data/README.md). El catálogo refleja lo publicado al 31-oct-2026; no es disponibilidad en tiempo real.

## Demo y evaluación

- **Comparador:** los 14 casos sintéticos de `data/examples/` dan el resultado esperado (14/14). Son entradas escritas a mano, no fotos ni salidas de IA.
- **Modelo:** evaluación con fotos reales **no ejecutada** todavía.
- Capturas de la demo: pendientes.

## Limitaciones

- Una foto no demuestra la composición de un objeto: si el símbolo del plástico no se distingue, se pide confirmarlo.
- Una regla ausente no significa prohibido ni aceptado: el resultado queda pendiente.
- Un solo centro documentado por ahora.
- Fuera del alcance: cuentas, mapas, rutas, WhatsApp, integraciones municipales y actualización automática del catálogo.

## Equipo

Estudiantes de Ingeniería de Sistemas y Computación de la UTP.

| Rol | Persona |
| --- | --- |
| A — IA y modelo | Emilia |
| B — Lógica y datos | José |
| C — Interfaz y producto | Noel |
| D — Integración y entrega | Ángel |

Las instrucciones para asistentes de código están en [AGENTS.md](AGENTS.md).
