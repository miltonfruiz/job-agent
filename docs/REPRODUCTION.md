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

## Correr el agente completo

```bash
uvicorn app.main:app --reload
# POST a /applications con job_posting + cv
```

## Correr la evaluación (baseline vs. agente)

```bash
# TODO: script que compare ats_score de ambos sobre el mismo set de casos
python -m tests.run_evaluation
```

## Datos requeridos

Vacantes y CVs de prueba en `starter_materials/` (sintéticos o públicos,
nunca información personal real de terceros).

## Runtime y costo aproximado

(completar una vez corridos los experimentos: tiempo por caso, costo en
tokens de Groq)

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
