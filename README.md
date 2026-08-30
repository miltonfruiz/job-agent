# Job Application Agent

## Quién tiene este problema

Un desarrollador (o cualquier profesional) que busca trabajo y necesita adaptar su CV
y carta de presentación a cada vacante distinta. Cada aplicación exige releer la
descripción del puesto, identificar qué skills destacar, reescribir secciones del CV
y redactar una carta desde cero.

## Cuál es el cuello de botella

Hacer esto manualmente para cada vacante es lento y propenso a inconsistencias:

- Se repiten los mismos errores de matching keyword/ATS en cada aplicación.
- No hay memoria entre aplicaciones (mismo error, distinta vacante).
- El resultado manual varía mucho en calidad según el cansancio/tiempo disponible.

## Por qué vale la pena resolverlo

Un agente que automatiza el 80% del trabajo mecánico (parseo de la vacante, tailoring
del CV, redacción de la carta, scoring ATS) deja al humano solo la decisión final de
aprobar o pedir ajustes — más rápido y más consistente que hacerlo a mano cada vez.

## Arquitectura

Ver `docs/ARCHITECTURE.md` para el diagrama y detalle de nodos del grafo LangGraph.

## Cómo correr esto

Ver `docs/REPRODUCTION.md` (guía de reproducción desde entorno limpio).

## Improvement Changelog

Ver `docs/CHANGELOG.md`.

## Estructura del repo

```
app/
  main.py           -> entrypoint FastAPI
  graph/            -> definición del grafo LangGraph (state, nodos, edges)
  db/                -> modelos y sesión de Postgres (memoria de aplicaciones)
  schemas/           -> schemas Pydantic (request/response de la API)
tests/               -> tests de baseline vs. agente
docs/                -> README técnico, changelog, guía de reproducción
trajectories/         -> logs de ejecución del agente (entregable del hackathon)
starter_materials/    -> CVs/vacantes de prueba (sintéticos o públicos)
```

## Baseline vs. solución avanzada

- **Baseline:** un único prompt a Groq pidiendo adaptar el CV a la vacante, sin
  herramientas, sin verificación, sin memoria.
- **Avanzada:** pipeline LangGraph con 4 tools especializados + verificación
  automática (grounding + ATS score) + checkpoint humano + memoria entre aplicaciones.

**Resultado real** (ver `docs/EVALUATION.md` para el detalle completo): sobre
las 3 vacantes de prueba, el agente tuvo **0 skills fabricadas** en todos los
casos. El baseline, sin ninguna verificación, fabricó 11, 3 y 15 skills
respectivamente para inflar su match — su score "en bruto" parece más alto,
pero no es confiable sin auditarlo a mano.

## Hot take

(completar al final, después de correr los experimentos)
