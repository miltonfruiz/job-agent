"""
Baseline: representa "lo que cualquiera podría armar en 5 minutos con un
prompt directo" - sin nodos separados, sin verificación de grounding, sin
checkpoint humano. Es el punto de comparación para medir si el agente
(app/graph/graph.py) realmente aporta una mejora medible.
"""

import re

import app.config  # noqa: F401  (carga las variables de .env como side effect)
from langchain_groq import ChatGroq

from app.graph.nodes import _MODEL_NAME, _invoke_with_retry

_BASELINE_SYSTEM_PROMPT = """Sos un asesor de carrera. Te van a dar una
vacante y un CV. Adaptá el CV a la vacante y escribí también una carta de
presentación.

Devolvé ambos con estos encabezados exactos, para poder separarlos:

## CV ADAPTADO
(el CV completo acá)

## CARTA DE PRESENTACIÓN
(la carta acá)"""


def _split_baseline_output(text: str) -> tuple[str, str]:
    """Separa el output combinado del baseline en CV y carta. Best-effort:
    si el modelo no siguió el formato de encabezados exactamente, devuelve
    todo como tailored_cv y una carta vacía en vez de romper.
    """
    parts = re.split(r"##\s*CARTA DE PRESENTACI[OÓ]N", text, flags=re.IGNORECASE)
    if len(parts) == 2:
        cv_part = re.sub(
            r"##\s*CV ADAPTADO", "", parts[0], flags=re.IGNORECASE
        ).strip()
        letter_part = parts[1].strip()
        return cv_part, letter_part
    return text.strip(), ""


def run_baseline(job_posting_raw: str, cv_raw: str) -> dict:
    llm = ChatGroq(
        model=_MODEL_NAME,
        temperature=0.3,
        max_tokens=4096,
        model_kwargs={"reasoning_effort": "low"},
    )

    human_message = f"Vacante:\n{job_posting_raw}\n\nCV original:\n{cv_raw}"

    result = _invoke_with_retry(
        llm,
        [
            ("system", _BASELINE_SYSTEM_PROMPT),
            ("human", human_message),
        ],
    )
    raw_output = result.content
    tailored_cv, cover_letter = _split_baseline_output(raw_output)

    return {
        "raw_output": raw_output,
        "tailored_cv": tailored_cv,
        "cover_letter": cover_letter,
    }