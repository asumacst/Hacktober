# IA — entrega del Rol A

## Integración para Ángel

El orquestador puede consumir la firma existente sin modificar contratos:

```python
from reciclaclaro.ai import identify
from reciclaclaro.contracts import AnalysisRequest, ReciclaClaroError

req = AnalysisRequest(image_bytes=image_bytes, mime_type="image/png")
try:
    result = identify(req)  # Gemini API real
    # result = identify(req, mock=True)  # Muestra fija, sin analizar la imagen
except ReciclaClaroError as exc:
    error = exc.error  # AppError: category, message, retryable
```

El código devuelve `IdentificationResult` y conserva los campos legados y nuevos.
Genera `analysis_id` e `item_id`; conserva las preguntas por atributo y proyecta
la primera en `pending_question`. No produce hechos confirmados ni aplica reglas.
Un nuevo análisis produce IDs nuevos. C conserva el ID durante las correcciones.

## Presentaciones y evidencia visual

El prompt usa el vocabulario del catálogo CAR: botella, envase, envase_huevos,
envase_ensalada, envase_ketchup, envase_sirope, tapita, espejo, ventana,
puerta_vidrio, mesa_vidrio, caja y caja_desarmada. Una presentación ambigua o
fuera de ese vocabulario produce una propuesta nula y una pregunta. No se infiere
resina por la marca o el contenido ni se fuerza coincidencia con reglas.
Las condiciones de preparación las recoge la UI según el catálogo; el análisis
visual no las convierte en hechos confirmados. Este ajuste requiere evaluación
con imágenes reales; las pruebas de transporte no demuestran su calidad visual.

## Configuración y límites iniciales

- Python con Pydantic 2, ya requerido por los contratos. Sin SDK adicional:
  transporte HTTP de la biblioteca estándar a Gemini API, `generateContent`.
- Clave de servidor en `GEMINI_API_KEY` o, como alternativa, `GOOGLE_API_KEY`.
  No hay carga automática de `.env`; D debe configurar el entorno.
- `GEMMA_MODEL`: por defecto `gemma-4-26b-a4b-it`; también admite
  `gemma-4-31b-it`. No cambia de variante silenciosamente.
- JPEG, PNG o WebP, máximo 8 MiB. Se comprueba tamaño y firma del contenedor;
  no se decodifica completamente la imagen. Archivos corruptos con cabecera
  válida pueden ser rechazados por el proveedor.
- Hasta 10 objetos, respuesta máxima 256 KiB y timeout de socket de 30 s por
  llamada. No es un plazo total garantizado. Un fallo de formato permite una
  segunda llamada; los fallos de API/red se devuelven sin reintento automático.
- JSON solicitado por prompt y validado con Pydantic; no se presupone soporte de
  JSON estructurado del proveedor. El reintento incluye tipos y ubicaciones del
  error de validación, sin copiar valores del modelo.
- `backend="local"` produce error explícito: Ollama no está implementado.
- `mock=True` requiere una entrada con tamaño y cabecera válidos, pero no la
  analiza. Devuelve una botella sintética desconocida y `is_mock=True`.
  `model_id` indica la variante configurada; con mock no significa una ejecución.

Los límites son decisiones iniciales de esta capa para revisión con D. No se
modificaron dependencias, orquestador, contratos, UI ni reglas compartidas.

## Validación y estado

Desde la raíz, con `src` en la ruta de Python:

```sh
PYTHONPATH=src python3 -B -m unittest discover -s tests -p test_ai.py -v
```

Las pruebas usan transporte simulado: no consumen API ni evalúan visión. Cubren
validación, límites, incertidumbre, IDs, recuperación de formato, metadatos,
timeout, errores HTTP y modo de ejemplo.

**Pendiente:** ejecutar una imagen autorizada con una clave real, comprobar la
calidad visual y la latencia, confirmar modelo elegido y conectar al orquestador.
La llamada real y la disponibilidad en la cuenta del equipo no están comprobadas.

Referencias oficiales consultadas el 31/10/2026:

- [Gemma mediante Gemini API](https://gemma.ai/deployment/gemini-api/)
- [Gemini generateContent](https://ai.google.dev/api/generate-content)

### Texto para que D integre en «Cómo usamos Gemma 4»

La capa de IA (`src/reciclaclaro/ai/client.py`) está preparada para enviar una
imagen a Gemma 4 mediante Gemini API. Propone objetos, materiales y preguntas
para revisión humana; el catálogo y el código determinístico deciden aceptación
y preparación. Valida la salida con Pydantic y permite un reintento de formato.
Incluye una muestra sin API identificada con `is_mock=True`. El modelo configurado
por defecto es `gemma-4-26b-a4b-it`; la ejecución real y la variante final siguen
pendientes de comprobación. No presentar esta implementación como integración
real verificada hasta registrar esa prueba.
