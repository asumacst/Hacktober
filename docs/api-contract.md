# Contratos de ReciclaClaro (PROPUESTA)

> **Estado: borrador.** Dueña: Rol A (Emilia). Aprueba: Rol D (Ángel).
> Redactado por el Rol C (Noel) para que IA, lógica, orquestador e interfaz trabajen en paralelo.
> Modelos en `src/reciclaclaro/contracts.py`. Una vez aprobado, solo cambios aditivos.

## Flujo y fronteras

```
Interfaz (C) ──AnalysisRequest──▶ Orquestador (D) ──▶ IA (A): Gemma 4
Interfaz (C) ◀─IdentificationResult─┘
Interfaz (C) ──ConfirmedItem[] + center_id──▶ Orquestador (D) ──▶ Lógica (B): catálogo + reglas
Interfaz (C) ◀─DeliveryPlan──────────────────┘
Cualquier capa ──ReciclaClaroError(AppError)──▶ Interfaz (C)
```

La interfaz **no** llama a Gemini ni a Ollama, no contiene prompts y no aplica reglas de centros.

## Interfaz del orquestador (propuesta para D)

```python
def identify(req: AnalysisRequest) -> IdentificationResult: ...
def list_centers() -> list[Center]: ...
def compare(items: list[ConfirmedItem], center_id: str) -> DeliveryPlan: ...
# Errores: raise ReciclaClaroError(AppError(...))
```

## Modelos

| Modelo | Campos | Quién lo produce |
| --- | --- | --- |
| `AnalysisRequest` | `image_bytes`, `mime_type`, `backend` (`gemini_api` por defecto, o `local`) | Interfaz |
| `DetectedItem` | `item_id`, `description`, `proposed_material`, `visible_evidence`, `pending_question` | IA |
| `IdentificationResult` | `items`, `model_id`, `backend`, `latency_ms`, `is_mock` | IA. Los 4 últimos los rellena el código |
| `ConfirmedItem` | `item_id`, `material`, `details`, `user_edited` | Interfaz (tras la confirmación humana) |
| `CenterRule` | `material`, `status`, `preparation`, `source_url`, `consulted_on` | Lógica y datos (catálogo) |
| `Center` | `center_id`, `name`, `rules`, `source_url`, `consulted_on` | Lógica y datos |
| `ComparisonResult` | `item_id`, `center_id`, `status`, `reason`, `preparation`, `rule_source_url`, `consulted_on` | Lógica |
| `DeliveryPlan` | `center`, `results`, `generated_at`, `input_fingerprint` | Orquestador |
| `AppError` | `category`, `message`, `retryable` | Cualquier capa |

- `status`: `aceptado`, `no_admitido` o `pendiente`. **Sin regla documentada → `pendiente`**, nunca aceptado ni prohibido.
- `Material`: `PET_1`, `HDPE_2`, `PP_5`, `aluminio`, `vidrio`, `papel_carton`, `desconocido`. A y B pueden ampliarlo.
- `backend`: lo elige la persona en la barra lateral. La implementación de cada proveedor es del Rol A. El modo `local` (Ollama) no sustituye el requisito de la Gemini API.
- `input_fingerprint`: si cambian la foto, los materiales confirmados o el centro, la interfaz descarta el plan anterior.
- `AppError.category`: `api`, `timeout`, `formato_invalido`, `entrada_invalida` o `sin_datos`.

## Ejemplos (datos de ejemplo, no reglas reales)

`IdentificationResult`:
```json
{
  "items": [
    {"item_id": "obj-1", "description": "Botella transparente", "proposed_material": "PET_1",
     "visible_evidence": "Símbolo 1 visible en la base", "pending_question": null},
    {"item_id": "obj-2", "description": "Envase blanco sin símbolo", "proposed_material": "desconocido",
     "visible_evidence": "No se distingue el símbolo", "pending_question": "¿Qué número tiene el símbolo de reciclaje?"}
  ],
  "model_id": "gemma-4-26b-a4b-it", "backend": "gemini_api", "latency_ms": 2100, "is_mock": true
}
```

`ComparisonResult`:
```json
{"item_id": "obj-2", "center_id": "centro-ejemplo", "status": "pendiente",
 "reason": "Material sin confirmar: falta el símbolo", "preparation": null,
 "rule_source_url": null, "consulted_on": null}
```

`AppError`:
```json
{"category": "timeout", "message": "Gemma tardó demasiado en responder. Intenta de nuevo.", "retryable": true}
```

## Pendientes de decisión (A y D)
- IDs de modelo: la documentación de Google lista `gemma-4-31b-it` y `gemma-4-26b-a4b-it` para la Gemini API. **No se han probado.**
- Tag local de Ollama (`gemma4`, sin confirmar) y si el modo local entra en el Tier 1.
- Límite de tamaño de imagen y tiempo máximo de espera.
- Ruta definitiva de `orchestrator.py` y de `data/centers.json`.
