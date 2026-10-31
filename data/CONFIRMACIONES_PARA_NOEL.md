# Confirmaciones que necesita el comparador del rol B

**Para:** Noel, con Emilia como revisora de contratos.  
**Estado:** guía del consumidor del catálogo actual; no modifica contratos ni UI.  
**Centro:** `car-fas-ciudad-del-saber`.  
**Revisión de fuentes:** 31/10/2026. Sin confirmación directa de vigencia.

El formulario debe permitir responder cada dato relevante con Sí, No o No sé.
La propuesta de Gemma puede mostrarse como sugerencia, pero solo una respuesta
explícita de la persona puede pasar a `attributes` como `user_confirmed`.

## Lo que bloquea actualmente la conexión

El formulario revisado recoge material, código de resina y limpieza. Falta recoger
la presentación y los atributos específicos de cada regla. Aunque una persona
confirme el material, el comparador devuelve `unknown` si no confirma también la
presentación. No es necesario cambiar el contrato para recoger estos datos.

## Confirmaciones por objeto

En todos los casos: `attributes.material` y `attributes.presentation` deben
coincidir con los campos `material` y `presentation` de `ConfirmedItem`.

| Material y presentación | Para decidir aceptación | Para poder mostrar listo |
| --- | --- | --- |
| `vidrio` / `envase` | Material y presentación confirmados. | `clean=true`, `residue_free=true`, `boxed=true`, `sorted_by_color=true`. |
| `vidrio` / `espejo`, `ventana`, `puerta_vidrio`, `mesa_vidrio` | Material y presentación confirmados. | No corresponde: exclusión documentada. |
| `PET_1` / `botella` | Confirmaciones básicas y `resin_code=1`. | `clean=true`, `residue_free=true`, `sorted_by_color=true`. |
| `PET_1` / `envase_huevos`, `envase_ensalada` | Confirmaciones básicas y `resin_code=1`. | No corresponde: exclusión documentada. |
| `HDPE_2` / `botella` | Confirmaciones básicas y `resin_code=2`. | `clean=true`, `residue_free=true`. |
| `PP_5` / `tapita` | Confirmaciones básicas y `resin_code=5`. | `clean=true`, `residue_free=true`. |
| `PP_5` / `envase_ketchup`, `envase_sirope` | Confirmaciones básicas y `resin_code=5`. | No corresponde: exclusiones específicas. |
| `PP_5` / `envase` genérico | Confirmaciones básicas y `resin_code=5`. | Queda pendiente de aclaración con el centro. |
| `papel_carton` / `caja`, `caja_desarmada` | `corrugated=true`; comprobar `wet`, `greasy` y `painted`. Cualquiera verdadero activa exclusión. Si faltan datos y no hay exclusión probada, queda pendiente. | Los tres anteriores falsos, `clean=true`, `residue_free=true` y presentación confirmada `caja_desarmada`. |
| Material desconocido o presentación no documentada | Solicitar identificación o aclaración. | No mostrar listo; no confundir falta de regla con rechazo. |

La separación por color se confirma contra la instrucción mostrada de la regla:
vidrio transparente, ámbar o verde; PET transparente, azul o verde. Si no encaja o
la persona no puede confirmarlo, debe responder No sé y consultar al centro.
`color` puede conservarse como dato adicional, pero la implementación actual no
lo usa como sustituto de `sorted_by_color` ni valida colores libres.

## Preguntas recomendadas

| Atributo | Pregunta para la persona | Tipo del valor confirmado |
| --- | --- | --- |
| `material` | ¿Confirmas este material después de revisar la evidencia? | Texto del enum `Material`. |
| `presentation` | ¿Qué tipo de objeto es: botella, envase, espejo, caja u otro? | Texto del vocabulario anterior; permitir desconocido. |
| `resin_code` | ¿Qué número aparece en el símbolo del plástico? | Entero 1–7, sin inferirlo por apariencia. |
| `clean` | ¿Está limpio? | Booleano. |
| `residue_free` | ¿Está libre de comida u otros residuos? | Booleano. |
| `boxed` | ¿Los envases de vidrio están dentro de una caja? | Booleano. |
| `sorted_by_color` | ¿Lo separaste siguiendo los colores indicados por el centro? | Booleano. |
| `corrugated` | ¿Es cartón corrugado? | Booleano. |
| `wet` | ¿Está mojado? | Booleano. |
| `greasy` | ¿Tiene grasa? | Booleano. |
| `painted` | ¿Está pintado? | Booleano. |

No todas las preguntas deben aparecer siempre. Usar material y presentación para
seleccionar las relevantes; `missing_data` indica dudas pendientes que ya detectó
el comparador. Un conflicto de fuentes puede quedar pendiente sin una pregunta
que la persona pueda resolver: en ese caso hace falta consultar al centro.

## Formato que ya acepta la lógica

Ejemplo sintético de envase de vidrio preparado:

```json
{
  "item_id": "obj-vidrio-1",
  "analysis_id": "analisis-ejemplo-1",
  "revision": 0,
  "material": "vidrio",
  "presentation": "envase",
  "attributes": {
    "material": {"value": "vidrio", "source": "user_confirmed"},
    "presentation": {"value": "envase", "source": "user_confirmed"},
    "clean": {"value": true, "source": "user_confirmed"},
    "residue_free": {"value": true, "source": "user_confirmed"},
    "boxed": {"value": true, "source": "user_confirmed"},
    "sorted_by_color": {"value": true, "source": "user_confirmed"}
  }
}
```

Un No explícito se transmite como `{"value": false, "source": "user_confirmed"}`.
Un No sé se transmite como `{"value": null, "source": "unknown"}` o se omite el
atributo. No usar `"true"`, `"false"`, `0` ni `1` como sustitutos de booleanos.
Para resina usar el entero `1`, no el texto `"1"` ni el booleano `true`.

## Cómo interpretar los resultados

| Resultado | Qué debe comunicar la pantalla |
| --- | --- |
| `accepted` + `ready` | Cumple las condiciones documentadas y confirmadas. Mostrar evidencia. |
| `accepted` + `action_required` | Material admitido, pero faltan acciones. Mostrarlas y las preguntas que puedan coexistir. |
| `accepted` + `unknown` | Preparación sin verificar; mostrar las preguntas disponibles. |
| `rejected` + `not_applicable` | Exclusión explícita con motivo y fuente. No sugerir limpieza como solución garantizada. |
| `unknown` + `unknown` | Datos o evidencia insuficientes; no comunicar aceptación ni prohibición. |

`status=aceptado` es compatibilidad con el contrato anterior, no prueba de que el
objeto esté listo. La etiqueta depende también de `preparation_status`.

## Correcciones y acuerdos pendientes

- Conservar `item_id` al corregir un objeto y confirmar de nuevo los datos que
  dependan del cambio. Cambiar de PET a vidrio no convierte la presentación en envase.
- Usar una revisión coherente para el conjunto de objetos; el comparador conserva
  los metadatos recibidos, no administra la sesión.
- Al desarmar una caja, confirmar la presentación `caja_desarmada`. Esta convención
  evita añadir un atributo nuevo al contrato y debe revisarse con Emilia.
- UI y orquestación deben invalidar el plan al cambiar foto, confirmaciones o centro.
- A y C deben acordar el vocabulario mostrado y su correspondencia con estos valores.

## Funciones del rol B disponibles

```python
from reciclaclaro.contracts import ConfirmedItem
from reciclaclaro.logic import load_centers, compare_item, compare_items

centers = load_centers()
center = next(c for c in centers if c.center_id == "car-fas-ciudad-del-saber")
item = ConfirmedItem.model_validate(payload_confirmado)
result = compare_item(item, center)
results = compare_items([item], center)
```

Las funciones no llaman a IA ni construyen `DeliveryPlan`. El código que conecte
las capas debe manejar un centro inexistente y `ReciclaClaroError`; no elegir otro
centro silenciosamente. Las firmas y clases compartidas permanecen intactas.

Ejemplos ejecutables en `examples/comparison_cases.json`; respuestas completas en
`examples/comparison_results.json`. Son datos sintéticos, no resultados de Gemma.
