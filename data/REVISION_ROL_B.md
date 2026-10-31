# Revisión de lógica y datos del rol B

**Fecha:** 31/10/2026.  
**Alcance:** catálogo, comparador, pruebas, ejemplos y documentación de esta capa.  
**Estado:** trabajo local para revisión; no se modifican IA, UI, contratos,
orquestador, dependencias ni instrucciones compartidas.

## Resultado

El catálogo contiene un centro, tres categorías y 18 reglas con identificadores
únicos y referencias. Hay 26 casos sintéticos etiquetados, incluidos aceptación,
exclusión, preparación pendiente y evidencia insuficiente. Sus resultados se
guardan junto con un informe de conteos y huellas de los archivos evaluados.

La guía [CONFIRMACIONES_PARA_NOEL.md](CONFIRMACIONES_PARA_NOEL.md) especifica qué
debe confirmar la persona para cada presentación, cómo representar un No frente
a un No sé y qué necesita mostrar la pantalla. Es documentación de nuestro
comparador; A y C siguen siendo responsables de sus capas y acuerdos compartidos.

## Hallazgos y correcciones

| Hallazgo reproducido | Corrección en esta capa |
| --- | --- |
| Los modelos compartidos ignoraban campos desconocidos al cargar el JSON; una condición mal escrita podía perderse. | La carga del catálogo rechaza campos no reconocidos, sin cambiar los modelos compartidos. |
| JSON permitía claves repetidas y reglas duplicadas con otro identificador. | Detectar claves duplicadas y firmas semánticas repetidas. |
| Una condición booleana podía contener un entero; la resina podía contradecir el material. | Verificar tipos y coherencia de las condiciones del catálogo. |
| Referencias estructuralmente presentes podían contener URLs o fechas incoherentes. | Validar referencias en carga y antes de producir decisiones definitivas. |
| Expectativas incompletas podían no verificar las dos dimensiones del resultado. | Exigir aceptación y preparación; rechazar corpus vacío, casos repetidos o centros inexistentes. |
| Los ejemplos solo comprobaban estados. | Permitir verificar también atributos faltantes y reglas aplicadas. |
| Los archivos de resultados podían quedarse desactualizados. | Pruebas comparan resultados e informes guardados con su regeneración actual. |
| Git puede convertir LF y CRLF al clonar en Windows. | Huellas de texto normalizadas para conservar reproducibilidad entre sistemas. |

Las regresiones del catálogo fallaron antes de las correcciones y pasaron después.
Las pruebas usan datos temporales y sintéticos; no necesitan red ni cuota de IA.

## Revisión de fuentes y pendientes

Se volvieron a consultar las páginas oficiales de
[FAS](https://faspanama.org/servicios/) y
[Ciudad del Saber](https://ciudaddelsaber.org/centro-de-acopio-de-reciclables-car)
el 31/10/2026.

FAS distingue tapitas PP admitidas de envases de kétchup y sirope excluidos. Se
añadieron esas dos exclusiones específicas. La descripción general de PP en la
página de Ciudad del Saber no demuestra que esos artículos particulares se
admitan. Los envases PP genéricos siguen pendientes de aclaración.

Las menciones de LDPE tampoco bastan para ampliar el enum ni aceptar otras
presentaciones. Las fechas de publicación y actualización no son visibles en las
páginas revisadas: se mantienen nulas. La consulta web no confirma operación
actual, capacidad de recepción, horarios excepcionales ni vigencia de cada regla.
No se contactó al centro ni se enviaron mensajes.

También apareció un [anuncio de reapertura del 08/10/2020](https://ciudaddelsaber.org/noticias/anunciamos-la-apertura-del-centro-de-acopio-de-reciclables-car)
con instrucciones de secado. Es histórico: no se usó para añadir una condición
vigente al catálogo de 2026.

## Evaluación reproducible

| Archivo | Qué acredita |
| --- | --- |
| `quality_report.json` | Perfil local del catálogo, reglas pendientes y confirmaciones por regla. |
| `examples/comparison_cases.json` | Entradas sintéticas y expectativas escritas por el rol B. |
| `examples/comparison_results.json` | Respuestas actuales y comprobaciones por caso. |
| `examples/evaluation_report.json` | Conteos, casos discrepantes y hashes de catálogo, corpus e implementación. |

Los casos son pequeños y fueron preparados dentro del mismo trabajo del rol B.
No son una evaluación independiente, un benchmark, una medida de precisión de
Gemma ni evidencia de reducción real de viajes o residuos. Se informan conteos,
sin extrapolar porcentajes de impacto.

## Validación realizada

Comando de pruebas con Python local y `PYTHONPATH=src`:

```powershell
python -B -m pytest tests/test_contracts.py tests/test_logic.py tests/test_catalog_quality.py tests/test_evaluation.py tests/ui/test_state.py -q -p no:cacheprovider
```

La selección incluye contratos, toda nuestra lógica, calidad del catálogo,
evaluación y las pruebas puras de estado de UI, sin modificar estas últimas.
No equivale a ejecutar la interfaz ni a probar el flujo con Gemma.

Resultado final de esta selección: **142 pruebas aprobadas**. El ejecutor confirmó
**26/26 casos sintéticos coincidentes**, y el perfil validó **18/18 reglas con
evidencia**. Los informes guardados coinciden con su regeneración. Streamlit no
está instalado en el intérprete comprobado; no se ejecutó la suite de componentes
visuales ni se verificó la interfaz en funcionamiento.

Las pruebas incluyen las 81 combinaciones Sí/No/No sé de las cuatro condiciones
de preparación del vidrio y las 27 combinaciones de humedad, grasa y pintura del
cartón. Una exclusión confirmada tiene prioridad; un dato desconocido no cuenta
como condición cumplida.

Para regenerar los informes:

```powershell
python -B -m reciclaclaro.logic.examples --output data/examples/comparison_results.json --report data/examples/evaluation_report.json
python -B -m reciclaclaro.logic.audit --output data/quality_report.json
```

El ejecutor de ejemplos admite `--cases` para otro corpus. Un caso discrepante
hace que termine con código 1; no se alteran las etiquetas para forzar coincidencias.

## Integración y límites

- Mantener `item_id`, metadatos y tipos de los contratos actuales.
- Revisión con A y C del vocabulario de presentaciones y preguntas de confirmación.
- UI y orquestación aún deben gestionar invalidación de planes y conexiones reales.
- Un No sé o una presentación fuera del subconjunto documentado permanece pendiente.
- `sorted_by_color` significa confirmación explícita de los colores de la regla;
  el campo libre `color` no se usa para inferir esa confirmación.
- La validez estructural de una fuente no prueba su contenido ni su vigencia.
- No se realizaron commits, push ni PRs durante esta revisión.
