# Contratos de ReciclaClaro (PROPUESTA)

Ampliación local del 31/10/2026 solicitada por José a partir de la respuesta de
Emilia. Conserva los modelos y campos de Noel. Pendiente de revisión de A y C y
aprobación de integración de D. El archivo Python ya expresa esta ampliación;
esto no significa que el comparador o el orquestador estén implementados.

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

## Ampliación con los parámetros propuestos por Emilia

Las tablas anteriores describen los campos originales, que se conservan. Esta
sección añade la información estructurada que necesitan los casos del CAR.
Se requiere Pydantic 2 para los validadores; no se modificaron dependencias.

### Identidad y confirmación humana

- Se conserva `item_id`: es el identificador de objeto que Emilia denomina
  `object_id`. No se añade un segundo identificador que pueda contradecirlo.
- `analysis_id` opcional se añade a `DetectedItem`, `IdentificationResult`,
  `ConfirmedItem`, `ComparisonResult` y `DeliveryPlan`. Lo genera el código,
  al igual que `item_id`. Una corrección conserva el objeto; otra foto inicia
  otro análisis. El contrato no genera identificadores automáticamente.
- `revision`, entero no negativo con valor inicial 0, se añade a los objetos
  confirmados, resultados y plan. D debe incrementarla para todo el conjunto de
  entrada cuando cambie un dato confirmado; no es un contador distinto por objeto.
- `input_fingerprint` se conserva como mecanismo original de invalidación de UI.
  D calcula su valor incluyendo foto/análisis, datos confirmados y centro; las
  revisiones aportan contexto verificable, no sustituyen ese cálculo. Una revisión
  sin cambios no permite detectar por sí sola una foto nueva.
- `DeliveryPlan` rechaza resultados cuyo centro, análisis o revisión no coincidan
  con el contexto del plan. No consulta el estado actual de la sesión: invalidar
  el plan anterior y comprobar su huella sigue siendo responsabilidad de D y C.

`ConfirmedItem` añade `presentation` y `attributes`. `DetectedItem` añade
`proposed_presentation` y `pending_questions`; las propuestas visuales permanecen
separadas de los datos confirmados. `details` y `user_edited` se conservan para
compatibilidad, pero no son evidencia de confirmación por atributo.

Cada entrada de `attributes` es `ConfirmedAttribute`:

| Campo | Valores y regla |
| --- | --- |
| `value` | Booleano, entero, texto o nulo. Los tipos escalares son estrictos. |
| `source` | `user_confirmed` exige valor; `unknown` exige nulo. No admite procedencia IA. |

Nombres de atributos iniciales: `material`, `presentation`, `resin_code`, `color`,
`clean`, `residue_free`, `corrugated`, `wet`, `greasy`, `painted`, `boxed` y
`sorted_by_color`. No todos son obligatorios: los determina la regla aplicable.
Las confirmaciones de material y presentación, cuando existen, deben coincidir
con los campos correspondientes. Un atributo ausente sigue sin confirmar.
La procedencia declarada no prueba por sí sola una interacción humana: C debe
recogerla de la persona, nunca copiar automáticamente propuestas de Gemma.

Ejemplo sintético de entrada confirmada:

```json
{
  "item_id": "obj-1", "analysis_id": "foto-1", "revision": 1,
  "material": "vidrio", "presentation": "envase",
  "attributes": {
    "material": {"value": "vidrio", "source": "user_confirmed"},
    "presentation": {"value": "envase", "source": "user_confirmed"},
    "clean": {"value": false, "source": "user_confirmed"},
    "color": {"value": null, "source": "unknown"}
  }
}
```

### Dos dimensiones del resultado

`ComparisonResult` añade:

| Campo | Contenido |
| --- | --- |
| `acceptance` | `accepted`, `rejected`, `unknown` |
| `preparation_status` | `ready`, `action_required`, `unknown`, `not_applicable` |
| `preparation_actions` | Lista de acciones documentadas por realizar |
| `missing_data` | Lista de `PendingQuestion`: `attribute` y `question` |
| `rule_references` | Lista de `RuleReference`: `rule_id` y una o más fuentes |

`status` se mantiene como proyección de aceptación para consumidores anteriores:

| `status` original | `acceptance` |
| --- | --- |
| `aceptado` | `accepted` |
| `no_admitido` | `rejected` |
| `pendiente` | `unknown` |

Se puede proporcionar una sola de las dos representaciones: se deriva la otra.
Si se proporcionan ambas y discrepan, la validación falla. El texto `preparation`
se conserva, pero no sustituye `preparation_status` ni demuestra que esté listo.

Reglas de coherencia:

- Rechazo implica preparación `not_applicable` y no admite acciones que prometan
  resolver el rechazo. Aceptación desconocida conserva preparación `unknown`.
- `ready` y `action_required` requieren aceptación `accepted`.
- `action_required` exige al menos una acción.
- `ready` exige referencias a reglas y no admite acciones ni datos pendientes.
- Un resultado antiguo aceptado sin información nueva conserva preparación
  `unknown`. Los consumidores deben usar ambas dimensiones antes de decir “listo”.

El contrato valida coherencia estructural. Solo el comparador puede comprobar si
las reglas y todas las condiciones aplicables se cumplen realmente; no se
implementa esa comprobación dentro de estos modelos.

### Reglas y fuentes

`CenterRule` conserva sus campos y añade `rule_id`, `presentation`, `conditions`,
`preparation_conditions`, `required_attributes` y `references`.
`conditions` describe coincidencias de atributos para aceptación o exclusión;
`preparation_conditions` describe condiciones de entrega. No son un motor de reglas.
No se deben interpretar condiciones de exclusión como instrucciones para limpiar.

`SourceReference` conserva URL (`url`), entidad (`entity`), fecha de consulta
(`consulted_on`) y fechas opcionales `published_on` y `updated_on`. Las fechas no
publicadas permanecen nulas. La fecha de consulta no las rellena automáticamente.

Los productores nuevos deben aportar identificadores estables de reglas y sus
fuentes. Los campos originales de URL y consulta siguen disponibles; las listas
estructuradas no se completan con fuentes inventadas. `rule_id` y referencias
admiten ausencia en reglas antiguas para permitir migración.

### Compatibilidad y pruebas

Los campos añadidos tienen valores por defecto. Se mantienen nombres de modelos,
materiales, estados originales y firmas propuestas del orquestador. Las nuevas
validaciones rechazan combinaciones contradictorias. Revisar con C consumidores
que dependan de un esquema JSON exacto, aunque puedan seguir leyendo campos previos.

Pruebas locales sin red en `tests/test_contracts.py`:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -m pytest tests/test_contracts.py -q -p no:cacheprovider
```

Las muestras son sintéticas. No prueban el catálogo real, la integración con
Gemma ni la invalidación efectiva de estado en UI/orquestador.
