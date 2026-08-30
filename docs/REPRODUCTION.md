# Guía de reproducción

## Requisitos

- Python 3.11+
- PostgreSQL corriendo localmente (o Docker)
- Una API key de Groq (https://console.groq.com)

## Setup desde cero

```bash
git clone <tu-repo>
cd job-application-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # completar GROQ_API_KEY y DATABASE_URL
```

## Correr el baseline

```bash
python scripts/run_baseline.py
```

Corre sobre todas las vacantes en `starter_materials/job_postings/`,
calcula el mismo ATS score que se usa para el agente, y guarda cada
resultado en `trajectories/baseline/`.

## Correr el agente completo (con checkpoint humano real)

```bash
python scripts/test_full_graph.py starter_materials/job_postings/job_01_fullstack.txt
```

Corre el grafo completo (parseo → tailoring → carta → verificación →
score → checkpoint humano real vía `interrupt()` → cierre), pidiendo tu
aprobación por consola. Guarda la trayectoria completa en `trajectories/`
y el paquete final (CV.md, cover_letter.md, ats_score.json) en `outputs/`.

_(Nota: la exposición vía FastAPI (`POST /applications`) está fuera de
alcance para esta entrega - el flujo completo ya está demostrado y es
reproducible vía este script.)_

## Correr la evaluación (baseline vs. agente)

```bash
python scripts/run_evaluation.py
```

Corre el agente (auto-aprobado, para medir en batch) y el baseline sobre
las 3 vacantes de `starter_materials/job_postings/`, y guarda la tabla
comparativa en `docs/EVALUATION.md`.

## Datos requeridos

Vacantes y CVs de prueba en `starter_materials/` (sintéticos o públicos,
nunca información personal real de terceros).

## Runtime y costo aproximado

Basado en las corridas reales hechas durante el desarrollo (modelo
`openai/gpt-oss-20b` en Groq, `reasoning_effort="low"`):

| Paso                                                                                           | Tiempo aproximado    | Costo                     |
| ---------------------------------------------------------------------------------------------- | -------------------- | ------------------------- |
| `parse_job` (1 llamada LLM)                                                                    | ~2-4 s               | Capa gratuita de Groq: $0 |
| `tailor_resume` (1 llamada LLM)                                                                | ~3-6 s               | $0                        |
| `generate_cover_letter` (1 llamada LLM)                                                        | ~3-5 s               | $0                        |
| `verify_grounding` (sin LLM, determinístico)                                                   | <0.1 s               | $0                        |
| `score_ats` (sin LLM, determinístico)                                                          | <0.1 s               | $0                        |
| **Total por aplicación** (sin reintento de grounding, sin contar el tiempo de revisión humana) | **~10-15 s**         | **$0**                    |
| Con 1 reintento de `verify_grounding` (vuelve a `tailor_resume` + `generate_cover_letter`)     | ~20-25 s adicionales | $0                        |

**Costo real de la capa gratuita de Groq:** $0 en dólares, pero con límite
de tokens (ver sección siguiente). Durante el desarrollo completo (todas
las iteraciones del changelog + baseline + evaluación sobre 3 vacantes)
se consumió casi el 100% del cupo diario de 200,000 tokens del modelo
`openai/gpt-oss-20b` en una sola sesión de trabajo intensivo. Para uso
normal (unas pocas aplicaciones por día), el cupo gratuito alcanza sin
problema.

## Límites de la capa gratuita de Groq

La capa gratuita tiene dos límites relevantes:

- **8000 tokens/minuto**: el código reintenta automáticamente con backoff
  exponencial ante un 429 (`_invoke_with_retry` en `app/graph/nodes.py`).
- **200,000 tokens/día**: este límite NO se resuelve con el retry corto
  (el reset puede tardar varios minutos). Si lo alcanzás, Groq indica
  cuánto esperar en el mensaje de error - hay que esperar ese tiempo y
  reintentar manualmente. Correr el pipeline completo (parse + tailor +
  carta) sobre varias vacantes, más el baseline y la evaluación, consume
  un volumen considerable del cupo diario en una sola sesión de pruebas
  intensivas.
  Si al reproducir esto ves errores de rate limit persistentes, esperá el
  tiempo indicado en el mensaje de error entre casos de prueba, o considerá
  una cuenta de pago para correr la evaluación completa sin interrupciones.

**Workaround real usado durante el desarrollo:** el límite diario es por
modelo. Si `openai/gpt-oss-20b` agota su cupo, se puede seguir trabajando
pasando `GROQ_MODEL=qwen/qwen3.6-27b` como variable de entorno (cupo
diario separado), sin tocar código:

```bash
GROQ_MODEL="qwen/qwen3.6-27b" python scripts/test_full_graph.py <vacante>
```
