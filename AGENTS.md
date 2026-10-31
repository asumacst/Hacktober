# ReciclaClaro — Contexto común del equipo

## Misión y producto elegido

ReciclaClaro es el proyecto elegido por el equipo de cuatro integrantes para
Hacktoberfest Hack Day Panama City 2026, el 31 de octubre de 2026.

Una persona en Panamá fotografía sus residuos, confirma los materiales propuestos
por Gemma 4 y obtiene un plan de preparación y entrega basado en las condiciones
documentadas del centro de acopio que elige.

**Flujo principal:** foto → identificación con Gemma → confirmación humana →
selección de centro → comparación determinística → plan con fuentes.

El problema no termina en determinar si un objeto es reciclable: hay que saber
cómo prepararlo y si el destino lo recibe. El usuario inicial separa residuos en
casa. Reducir dudas y viajes fallidos es un beneficio esperado por validar.

Gaceta Viva, el analista empresarial y las otras ideas evaluadas no son el alcance
del proyecto. No añadir agentes o infraestructura de esas propuestas.

## Autoridad y estado de las decisiones

- La tarea vigente y las decisiones explícitas del equipo delimitan el trabajo.
- Este archivo es común para integrantes y asistentes; no asigna a toda sesión
  un mismo rol personal.
- `AGENTS.md` es la fuente común de instrucciones. `CLAUDE.md` lo importa para
  Claude Code; actualizar aquí los datos compartidos para evitar divergencias.
  El repositorio debe ser autocontenido: no depender de archivos de la carpeta
  superior de una máquina. Un contexto personal puede precisar el rol propio,
  pero no cambiar contratos ni reglas compartidas.
- Leer código, README y contratos antes de editar. Consultar `docs/architecture.md`,
  `docs/api-contract.md`, `docs/decisions.md` y `docs/design-system.md` si existen;
  no asumir que están creados o actualizados.
- La propuesta plantea Python, Streamlit, SDK de Gemini API, validación de
  respuestas y catálogo JSON. Es una propuesta, no evidencia de implementación.
  Confirmar stack y rutas antes de crear archivos o dependencias.
- Documentar decisiones compartidas en el repositorio. Señalar discrepancias entre
  código y documentación; no reescribir contratos unilateralmente.
- Confirmar modelo exacto, centros iniciales, licencia y rutas definitivas por rol,
  y registrarlos en el README. No confundir stack previsto con código ya construido.

## Alcance y prioridades

### Tier 1 — Flujo imprescindible

1. Subir una foto con pocos objetos y ejecutar una llamada real a Gemma 4.
2. Mostrar objetos, materiales propuestos y datos pendientes de confirmar.
3. Permitir corregir y confirmar los materiales antes de compararlos.
4. Seleccionar al menos un centro con reglas, fuentes y fechas documentadas.
5. Mostrar qué llevar, cómo prepararlo y qué no puede resolverse con la evidencia.
6. Disponer de README reproducible y licencia abierta acordada.

### Tier 2 — Después de completar el flujo

Hasta tres centros, fuentes y fechas visibles en cada decisión, errores
recuperables y evaluación registrada de al menos tres casos.

### Tier 3 — Solo con entrega asegurada

Comparar destinos, descargar el plan y preferencias de ubicación.

Fuera del alcance de la hackatón: cuentas, mapas interactivos, rutas, WhatsApp,
integraciones municipales, actualización automática y entrenamiento de modelos.
Recorte de emergencia: un centro y tres categorías, conservando la llamada real,
confirmación humana y plan verificable.

## Arquitectura y fronteras

- **Interfaz:** foto, revisión, correcciones, centro, resultados y fuentes.
- **Orquestación:** conecta las capas y controla el flujo y los errores.
- **IA:** Gemma 4 interpreta la imagen y propone objetos, materiales y preguntas.
- **Lógica y datos:** código determinístico consulta el catálogo y aplica reglas
  a los materiales confirmados. La aceptación no la decide libremente el modelo.

La UI consume el orquestador o API acordada. No duplicar prompts, clientes de Gemma
o reglas en componentes visuales. Una API HTTP separada no es obligatoria: usar
los límites del stack elegido.

### Contratos antes de construir

A mantiene los contratos; D coordina su integración y aprueba cambios compartidos.
B y C participan como consumidores. Documentar en un archivo acordado:

| Intercambio | Información mínima que debe definirse |
| --- | --- |
| Identificación de IA | ID de objeto, descripción, material propuesto, evidencia visible y pregunta pendiente. |
| Material confirmado | ID, material y detalles confirmados por el usuario. |
| Centro | Identificador, nombre, materiales, condiciones, fuente y fecha de consulta. |
| Comparación | Objeto, centro, estado, motivo, preparación y fuente de la regla. |
| Error | Categoría, mensaje utilizable y posibilidad de reintento. |

La tabla expresa necesidades, no nombres definitivos de campos, endpoints o enums.
Priorizar cambios compatibles y aditivos. No romper consumidores ni modificar
contratos sin coordinación. Modelo usado, tiempos y valores calculados se rellenan
en código, no se delegan al modelo.

## Fiabilidad y evidencia

- Una foto no demuestra por sí sola la composición. Si el símbolo del plástico
  no se distingue, pedir otra imagen o confirmación manual.
- La IA no inventa centros, horarios, reglas, fuentes ni fechas. El catálogo
  documentado determina las condiciones de recepción.
- Falta de evidencia significa pendiente de confirmar. No confundir una regla
  ausente con prohibición explícita ni aceptación.
- Cada decisión debe mostrar regla, fuente y fecha de consulta. No prometer
  disponibilidad en tiempo real ni usar anuncios antiguos como vigencia actual.
- Cambiar foto, materiales confirmados o centro invalida el plan anterior.
- Validar entradas y respuestas. Limitar archivos y solicitudes; manejar timeouts,
  errores de API y formato inválido con reintentos acotados, sin bucles indefinidos.
- Etiquetar mocks y resultados guardados: sirven para desarrollo y respaldo, pero
  no demuestran integración real ni elegibilidad del reto.
- No inventar porcentajes de precisión, impacto o resultados de pruebas.

## Distribución del trabajo

| Rol | Persona | Propiedad y entregable | Rutas propuestas |
| --- | --- | --- | --- |
| A — IA y modelo | Emilia | Cliente de Gemma, prompts, validación y contratos. Objetos identificados con dudas explícitas. | `src/reciclaclaro/ai/`; archivo de contratos por acordar. |
| B — Lógica y datos | José | Fuentes, catálogo, comparación y pruebas determinísticas. Decisiones verificables. | `src/reciclaclaro/logic/`, `data/` y pruebas de su capa. |
| C — Interfaz y producto | Noel | Pantallas, estado, correcciones, consumo de API/orquestador, plan y demo. Recorrido visible completo. | `src/reciclaclaro/ui/`; guion y capturas en coordinación con D. |
| D — Integración y entrega | Ángel | Orquestador compartido, estructura, dependencias, configuración, CI, README, licencia e integración final. Ejecución reproducible. | Raíz, configuración y `docs/`; ruta del orquestador por acordar. |

Las asignaciones se consolidan del CLAUDE.md del proyecto y de la confirmación de
Noel como C. Las rutas son propuestas hasta que D defina la estructura: no crear
ni reclamar carpetas por esta tabla. Cada rol escribe las pruebas de su capa;
`tests/` no es propiedad exclusiva de B.

Respaldo: A ↔ B y C ↔ D. Cada rol prueba y documenta su parte; D integra la
documentación. Las conexiones de API de C no transfieren la propiedad del cliente
del modelo de A ni del orquestador compartido de D.

Asignar archivos antes de trabajar en paralelo. Las responsabilidades no dependen
del asistente utilizado. D coordina integración; ningún asistente recibe permiso
automático para publicar, mergear o modificar la rama principal.

## Operación de asistentes y Git

1. Comprobar directorio, rama, estado de Git y archivos de la tarea. No asumir que
   la rama principal se llama `main` ni que un ejemplo es la rama asignada.
2. Leer lo necesario y definir un criterio observable de aceptación. Avanzar dentro
   del alcance autorizado; consultar bloqueos que afecten contratos, trabajo ajeno
   o decisiones compartidas.
   Comunicar un plan corto para tareas con varios pasos; una tarea ya autorizada
   no exige otro permiso para cada cambio rutinario dentro de su alcance.
3. Hacer cambios pequeños y reversibles en archivos asignados. Preservar cambios
   sin commit y no tocar worktrees o archivos de otros integrantes.
4. Evitar refactors, renombres y dependencias innecesarios. Coordinar dependencias
   nuevas con D; no imponer rutas o comandos sin verificar el repositorio.
5. Ejecutar comprobaciones pertinentes y revisar el diff antes de entregar.
6. No cambiar de rama, resetear, rebasear, forzar push o eliminar trabajo ajeno sin
   autorización. Commits, push, PRs y merges requieren solicitud o autorización
   explícita de la tarea; el cargo de un integrante no equivale a permiso.
7. No cambiar políticas compartidas silenciosamente. La asignación local personal
   debe quedar fuera del historial compartido y no redefinir roles ajenos.

### Repositorio e integración

- Repositorio: `https://github.com/asumacst/Hacktober`. La rama principal es
  **`master`**, confirmada en GitHub; las referencias a `main` de documentos
  genéricos significan la rama principal, no una orden de crearla o renombrarla.
- Una rama corta por tarea, preferiblemente `feature/<persona>-<tema>`; respetar
  ramas ya asignadas. Sincronizar con la base sin sobrescribir trabajo pendiente.
- Commits pequeños con prefijos `feat`, `fix`, `test`, `docs` o `chore`.
- Flujo habitual: PR con alcance, validación y resultados; revisión y squash merge
  coordinados por D, con C como respaldo. Una instrucción explícita de publicar en
  la rama principal autoriza esa operación concreta; no otorga permiso general.
- Ventanas internas de integración propuestas: a los :20 y :50. No integrarlas
  automáticamente ni posponer un bloqueo crítico por esperar una ventana.
- Marcar gates comprobados con tags como `g1-ok` y `g2-ok` cuando se solicite.
  Si la base se rompe, D coordina la recuperación del último estado funcional.
  Un revert requiere autorización y debe considerar los commits posteriores;
  nunca usar force-push o restaurar archivos ajenos a ciegas.

## Seguridad y configuración

- Leer credenciales mediante variables de entorno; ejemplos sin valores reales.
  No imprimir ni copiar claves en código, logs, capturas o documentación.
- Mantener claves de Gemini en ejecución de servidor, nunca en el navegador.
- No recopilar archivos de credenciales como contexto ni añadirlos al repositorio.
- Si aparece una credencial expuesta, señalarlo sin reproducirla y coordinar su
  revocación y rotación. Borrarla del último archivo no revoca una clave publicada.
- No guardar ni publicar fotos privadas sin necesidad y autorización. Usar ejemplos
  autorizados y documentar qué datos se envían al proveedor de IA.

## Validación y cierre de tareas

Separar pruebas del comparador de evaluación visual del modelo. Las pruebas
automatizadas de lógica no deben usar red ni consumir cuota de Gemini. Usar las
herramientas existentes; no afirmar que existen tests, build o lint sin comprobarlo.
Las funciones públicas nuevas que añadan comportamiento deben tener pruebas
pertinentes de su contrato, incluyendo bordes; evitar pruebas que solo repitan la
implementación. Para cambios exclusivamente documentales, revisar contenido,
referencias y diff sin inventar una ejecución de la aplicación.

Casos mínimos: foto clara, material ambiguo, material explícitamente no admitido,
datos insuficientes, error de API y recuperación. Verificar que las correcciones
afectan el plan y que un resultado anterior no permanece como vigente.

Terminado significa flujo real completo, incertidumbre visible, reglas con
evidencia, errores controlados, comprobaciones pertinentes ejecutadas y README
que permita arrancar desde un clon limpio en otra máquina. Documentar modelo
exacto, Gemini API, fuentes, limitaciones, evaluación, licencia y equipo.

Al terminar cada tarea reportar: **Implementado**, **Archivos**, **Validación**
(comandos y resultados reales), **Integración** y **Pendientes o bloqueos**.
Distinguir código probado, supuestos, mocks y trabajo faltante.

## Entrega y contexto del evento

Horarios de Panamá (UTC−5), según el playbook del equipo: congelar funcionalidades
a las 13:30; verificar instalación, documentación y respaldo a las 13:45; enviar
la entrega a las 14:00. El cierre indicado es a las 14:15; no confundir metas
internas con plazos oficiales. Tras el congelamiento priorizar fallos de la demo.

El contexto compartido de los retos requiere proyecto nuevo desarrollado durante
el evento, repositorio público y licencia abierta para Best Open-Source AI Project,
y Gemma 4 funcionando mediante Gemini API para Best Use of Gemma 4. Probar el modelo
exacto con imagen real y documentarlo; Ollama local no sustituye ese requisito.
La doble postulación necesita confirmación de los organizadores. El contexto indica
registro y check-in de los cuatro y un máximo de un reto ganado por equipo.

Context.txt destaca creatividad y organización del repositorio como criterios;
no se conocen pesos ni una rúbrica completa. No inventar reglas o capacidades.
Las reglas se registran como contexto proporcionado por el equipo, no como una
verificación externa realizada por este archivo.

## Procedencia del contexto

Este archivo sintetiza `ReciclaClaro_Propuesta_Hackathon.md`, el playbook estratégico,
Context.txt y la selección explícita de ReciclaClaro y del Rol C para Noel. Esos
documentos se consultaron en la carpeta de planificación superior; no asumir que
estarán disponibles en otros clones.

El documento de subagentes usa otra distribución que atribuye integración y
propiedad de main a Noel. No usarla para sustituir los roles A–D anteriores ni
reinterpretar las asignaciones consolidadas aquí. Confirmar y registrar cambios
de responsabilidades como decisiones del equipo.

## Pendientes del proyecto

- Probar el modelo exacto de Gemma 4 mediante Gemini API con una imagen real.
- Confirmar con organizadores la doble postulación.
- Acordar estructura definitiva, archivo de contratos y configuración de entorno.
- Documentar el primer centro de acopio, reglas, fuentes y fechas.
- Seleccionar licencia abierta y completar README e instalación reproducible.
