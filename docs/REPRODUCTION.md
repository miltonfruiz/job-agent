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
# TODO: script tests/run_baseline.py que corra el prompt único
# sobre starter_materials/ y guarde resultados en trajectories/
python -m tests.run_baseline
```

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
