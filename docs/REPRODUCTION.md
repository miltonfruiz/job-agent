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

La capa gratuita limita a 8000 tokens/minuto. Correr el grafo completo
(parse_job + tailor_resume + generate_cover_letter, con prompts largos
por el CV completo) puede acercarse a ese límite si se corren varios
casos seguidos. El código reintenta automáticamente con backoff
exponencial ante un 429 (`_invoke_with_retry` en `app/graph/nodes.py`).
Si al reproducir esto ves errores de rate limit persistentes, esperá
~60 segundos entre casos de prueba o considerá una cuenta de pago.
