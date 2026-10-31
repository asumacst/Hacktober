# Carpeta `ui/` — propiedad del Rol C (Noel)

Complementa `AGENTS.md` de la raíz; no lo reemplaza.

## Para asistentes de otros roles
- **No modificar archivos de esta carpeta.** Si la interfaz necesita un cambio, descríbelo y pídeselo a Noel por el canal del equipo.
- Si cambias un contrato o la firma del orquestador, avísale a Noel antes del merge: la interfaz los consume.

## Qué hace la interfaz
Pantallas, estado de la sesión, confirmación de materiales, selección de centro, plan con evidencia, errores y demo. Streamlit: `streamlit run src/reciclaclaro/ui/app.py`.

## Qué no hace
- No llama a Gemini ni a Ollama, ni importa `google.genai` u `ollama`.
- No contiene prompts ni aplica reglas de centros.
- No edita `contracts.py`, el orquestador, `ai/`, `logic/` ni `data/`.

## Qué consume
- `src/reciclaclaro/contracts.py` (propuesta en `docs/api-contract.md`).
- Del orquestador: `identify`, `list_centers` y `compare`.
- Modo de trabajo: `RECICLACLARO_UI_MODE=mock` usa respuestas de ejemplo de `ui/fixtures/`, etiquetadas como MOCK; `live` usa el orquestador.

## Qué necesita de cada rol
| Rol | Necesita |
| --- | --- |
| A — Emilia | Contratos aprobados y el campo opcional `backend` (`gemini_api` / `local`) |
| B — José | `centers.json` válido según `Center`, con al menos un centro, fuente y fecha |
| D — Ángel | `orchestrator.py` con las 3 funciones (aunque sean stubs) y la versión de Streamlit en las dependencias |

## Archivos y worktrees de Noel
| Worktree | Rama | Archivos |
| --- | --- | --- |
| Claude Code | `feature/noel` | `app.py`, `state.py`, `components.py`, `AGENTS.md`, `CLAUDE.md` |
| Codex | `feature/noel-codex` | `client.py`, `fixtures/`, `tests/ui/` |
