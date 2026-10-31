# Decisiones del equipo

Registro de decisiones compartidas de ReciclaClaro. Lo mantiene el Rol D (Ángel). Una decisión nueva se agrega abajo; una que cambia se marca como reemplazada, no se borra.

| Fecha | Decisión | Motivo | Quién | Estado |
| --- | --- | --- | --- | --- |
| 31-oct-2026 | Rama principal: `master` | Es la rama creada en GitHub; no se crea ni renombra `main` | Equipo | Vigente |
| 31-oct-2026 | Licencia MIT | Licencia abierta recomendada por el playbook; GitHub la detecta | D | Por confirmar con el equipo |
| 31-oct-2026 | Modelo: `gemma-4-26b-a4b-it` vía Gemini API; respaldo `gemma-4-31b-it` | Ver detalle abajo | D, con A | Elegido; falta la prueba real con imagen (A) |
| 31-oct-2026 | Fotos de hasta 5 MB | Limitar el tamaño de las solicitudes | D | Propuesta; A confirma |

## Modelo de Gemma 4

La Gemini API ofrece dos modelos Gemma 4: `gemma-4-31b-it` y `gemma-4-26b-a4b-it`. Ambos aceptan imágenes y se usan con el SDK `google-genai` ([documentación de Google](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api?hl=en), consultada el 31-oct-2026).

Elegimos `gemma-4-26b-a4b-it` porque:

- Es un modelo de mezcla de expertos que activa solo una parte de sus parámetros por respuesta, lo que debería dar menos latencia en la demo en vivo. Es una expectativa; se confirma midiendo `latency_ms`.
- Es el modelo de los ejemplos oficiales de la Gemini API y el que ya usa el ejemplo de `docs/api-contract.md`.
- Si la calidad no alcanza en los casos de demo o hay errores de cuota, se cambia a `gemma-4-31b-it` editando solo `GEMINI_MODEL`.

Notas para el Rol A:

- La documentación no menciona salida JSON estructurada para Gemma: pedir JSON en el prompt y validarlo con los modelos de `contracts.py`, con un reintento acotado.
- El razonamiento interno ("thinking") se puede desactivar con `thinking_level="minimal"`; probar si reduce la latencia sin bajar la calidad.
- La clave se lee de `GEMINI_API_KEY`, que es la variable que usa `genai.Client()` por defecto.
- La página oficial muestra un aviso de que esa documentación migra a gemma.ai; los identificadores de modelo deben confirmarse con una llamada real.
