# Catálogo y ejemplos del comparador de ReciclaClaro

Implementación local del rol B sobre los contratos actuales, pendiente de revisión
con A y C antes de integrar. No contiene llamadas a Gemma, orquestador ni interfaz.

## Archivos

- `centers.json`: array de `Center`, compatible con `contracts.py`.
- `examples/comparison_cases.json`: 26 entradas sintéticas y estados esperados.
- `examples/comparison_results.json`: resultados obtenidos al ejecutar esas entradas.
- `src/reciclaclaro/logic/`: carga del catálogo, comparador y ejecución de ejemplos.
- `tests/test_logic.py`: pruebas de decisiones y fallos de datos.
- `CONFIRMACIONES_PARA_NOEL.md`: preguntas, tipos y valores necesarios en UI.
- `quality_report.json`: perfil local reproducible del catálogo.
- `examples/evaluation_report.json`: conteos de evaluación y huellas de los archivos evaluados.
- `REVISION_ROL_B.md`: revisión de evidencia, alcance y limitaciones.

Los ejemplos tienen `is_mock: true`: no son fotografías reales ni salidas de IA.
Los resultados esperados fueron especificados separadamente de las funciones;
el ejecutor informa si lo obtenido coincide.

## Centro y procedencia

CAR Ciudad del Saber, operado por FAS Panamá con apoyo de Fundación Ciudad del
Saber. Ubicación publicada: calle Rodolfo Benítez, local 216, Clayton, Panamá.
Contacto publicado: 317-8197 y faspanamaproyectos2019@gmail.com.

Fuentes consultadas durante la investigación del 31/10/2026:

| Fuente | Uso |
| --- | --- |
| [FAS — Servicios](https://faspanama.org/servicios/) | Aceptación, exclusiones y entrega. |
| [Ciudad del Saber — CAR](https://ciudaddelsaber.org/centro-de-acopio-de-reciclables-car) | Operador y condición general de limpieza sin residuos. |
| [FAS — Contacto](https://faspanama.org/contactenos/) | Ubicación y contacto. |

No se publicó una fecha de actualización visible en las páginas revisadas.
`published_on` y `updated_on` quedan nulos: no se sustituyen por la fecha de consulta.
No se contactó al centro y no se garantiza disponibilidad o vigencia en tiempo real.

## Alcance del catálogo

18 reglas en tres categorías: plástico, cartón y vidrio. Es un subconjunto de lo
publicado; la ausencia de una regla no constituye prohibición.

| Material | Subconjunto modelado |
| --- | --- |
| Vidrio | Envases; exclusiones de espejo, ventana, puerta y mesa de vidrio. |
| PET #1 | Botella; exclusiones de envases de huevos y ensalada. |
| HDPE #2 | Solo botella; otras presentaciones permanecen pendientes. |
| PP #5 | Tapita; exclusiones específicas para kétchup y sirope. Envases genéricos pendientes. |
| Papel/cartón | Solo cajas de cartón corrugado; exclusiones por humedad, grasa o pintura. |

No extender automáticamente aceptación de botella a cualquier envase del mismo
polímero. FAS y Ciudad del Saber no describen todos los plásticos con el mismo
alcance: la regla `fas-car-pp-envase-por-confirmar` conserva esa incertidumbre y
ambas referencias. LDPE #4 no se incorpora como material nuevo al contrato.

## Confirmaciones que necesita la interfaz

Se usan los modelos existentes sin modificar contratos ni firmas del orquestador.
`material` y `presentation` requieren confirmación individual en `attributes`.
`details`, `user_edited` y la mera presencia del material no confirman atributos.

| Atributo | Tipo y significado |
| --- | --- |
| `material`, `presentation` | Texto que coincide con los campos del objeto. |
| `resin_code` | Entero del 1 al 7, confirmado manualmente; no texto ni booleano. |
| `clean`, `residue_free` | Booleanos independientes. |
| `corrugated`, `wet`, `greasy`, `painted` | Booleanos de condición del cartón. |
| `boxed` | Envases de vidrio dentro de caja. |
| `sorted_by_color` | La persona confirma separación según los colores de la instrucción de la regla. |

Presentaciones de este catálogo: `envase`, `espejo`, `ventana`, `puerta_vidrio`,
`mesa_vidrio`, `botella`, `envase_huevos`, `envase_ensalada`, `tapita`, `caja` y
`caja_desarmada`. Son vocabulario del catálogo y ejemplos, no un enum compartido
nuevo. Confirmarlo con A y C; no deducirlo analizando el texto libre de `details`.

Para el cartón, pasar de `caja` a `caja_desarmada` permite confirmar el desarmado
sin inventar un atributo que el contrato actual no tiene. Se conserva el `item_id`
y se incrementa la revisión al corregirlo. Esta convención debe revisarse con A y C.

Para vidrio, la confirmación de separación corresponde a transparente, ámbar y
verde; para PET, a transparente, azul y verde. No afirmar cumplimiento basándose
solo en un color propuesto por la IA. Casos de otros colores requieren aclaración.

## Comportamiento

1. Datos sin confirmar o de tipo inadecuado producen preguntas; no se adivinan.
2. Se evalúan material, presentación y condiciones por igualdad de valor y tipo.
3. Una exclusión documentada que se cumple tiene prioridad sobre aceptación.
4. Una exclusión posible con datos faltantes bloquea la aceptación; un conflicto
   marcado como pendiente conserva el estado desconocido.
5. La aceptación no implica preparación lista. Las condiciones incumplidas producen
   acciones; las desconocidas, preguntas. Pueden coexistir acciones y preguntas.
6. Solo se marca `ready` con evidencia y sin condiciones pendientes. Una instrucción
   de preparación sin criterios estructurados no se considera cumplida por defecto.
7. Una regla ausente o sin fuentes suficientes nunca produce aceptación o rechazo.

No hay caché de decisiones. Cada llamada evalúa nuevamente los datos recibidos y
conserva `analysis_id`, `revision` y `center_id`. El orquestador y la interfaz aún
deben invalidar planes anteriores; estas funciones no manipulan su estado ni
calculan `input_fingerprint`.

## Uso desde el orquestador

```python
from reciclaclaro.contracts import ConfirmedItem
from reciclaclaro.logic import load_centers, compare_items

centers = load_centers()  # ruta local predeterminada, no depende del cwd
center = next(c for c in centers if c.center_id == "car-fas-ciudad-del-saber")
items = [ConfirmedItem.model_validate(payload) for payload in confirmed_payloads]
results = compare_items(items, center)
```

`compare_item(item, center)` devuelve `ComparisonResult`; `compare_items` devuelve
una lista ordenada. D construye `DeliveryPlan`, su fecha y huella. La capa llamadora
debe resolver un `center_id` desconocido mediante `AppError`, no elegir otro centro
silenciosamente. La carga y los errores de entrada utilizan `ReciclaClaroError`.

Una lista vacía devuelve resultados vacíos. Una lista con identificadores repetidos
o contextos de análisis/revisión distintos se rechaza. Un catálogo vacío o corrupto
genera error explícito, no falsos rechazos de materiales.

## Verificación local

Usar el Python del proyecto que tenga Pydantic 2 y pytest. No se añadieron paquetes
ni se cambiaron archivos de dependencias.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -B -m pytest tests/test_contracts.py tests/test_logic.py tests/test_catalog_quality.py tests/test_evaluation.py -q -p no:cacheprovider
python -B -m reciclaclaro.logic.examples --output data/examples/comparison_results.json --report data/examples/evaluation_report.json
python -B -m reciclaclaro.logic.audit --output data/quality_report.json
```

Perfil del catálogo comprobado: 1 centro, 18 identificadores de regla únicos y todas
las reglas con referencias. Las fechas de publicación ausentes son datos no
disponibles, no un motivo para rellenarlas por estimación.

La carga rechaza campos desconocidos, claves JSON duplicadas, reglas duplicadas,
condiciones de tipo incorrecto, códigos de resina incoherentes y referencias con
fechas o URLs inválidas. Son validaciones locales: no comprueban disponibilidad
web ni vigencia operativa. Los contratos compartidos permanecen sin cambios.

La evaluación exige ambas dimensiones esperadas; un objeto de expectativas vacío
no puede contar como acierto. Los casos que incluyen preguntas o reglas esperadas
también verifican esos datos. El informe registra hashes SHA-256 del catálogo,
corpus e implementación para reconocer qué archivos produjeron los resultados.
Las huellas normalizan BOM y saltos CRLF/LF, para poder verificarlas tanto en
Windows como en otros sistemas después de un checkout.

## Pendientes de integración

- A y C deben revisar el vocabulario y la confirmación por atributo con los ejemplos.
- Resolver con el centro la vigencia, las presentaciones HDPE adicionales y el
  alcance de envases PP/LDPE. Mantener estos huecos sin aceptación automática.
- Conectar resultados al orquestador y probar cambios de foto, material y centro
  en la interfaz real. Las pruebas actuales solo ejercitan esta capa y contratos.
- Mantener el catálogo como instantánea documentada, no como inventario en vivo.
