"""
Cada función es un nodo del grafo. Reciben y devuelven un dict parcial
que LangGraph mergea sobre el AgentState.

Convención: cada nodo apendea un entry a trajectory_log con
{node, input_summary, output_summary, timestamp} para el entregable
de "agent trajectories" del hackathon.
"""

import json

import app.config  # noqa: F401  (carga las variables de .env como side effect)
from langchain_groq import ChatGroq

from app.graph.state import AgentState
from app.graph.trajectory import log_step
from app.schemas.job_requirements import JobRequirements

# Modelo rápido para iterar durante el desarrollo. Groq deprecó los modelos
# Llama (llama-3.1-8b-instant / llama-3.3-70b-versatile) en agosto 2026;
# gpt-oss-20b es el reemplazo recomendado para uso rápido/económico.
# Evaluar al final del hackathon si openai/gpt-oss-120b mejora el score ATS
# lo suficiente como para justificar la latencia extra en la solución
# "avanzada" (ver docs/CHANGELOG.md).
_MODEL_NAME = "openai/gpt-oss-20b"

_PARSE_JOB_SYSTEM_PROMPT = """Sos un analista de reclutamiento técnico.
Tu tarea es leer una descripción de vacante y extraer, de forma objetiva
y sin inventar información que no esté en el texto:
- el nivel de seniority esperado
- las skills obligatorias (must_have_skills)
- las skills deseables pero no obligatorias (nice_to_have_skills)
- las keywords que probablemente un sistema ATS escanea (tecnologías,
  certificaciones, metodologías, herramientas)
- un resumen de 1-2 líneas del rol

Si algo no está explícito en el texto, no lo infieras ni lo completes con
suposiciones."""


def parse_job(state: AgentState) -> dict:
    llm = ChatGroq(model=_MODEL_NAME, temperature=0)
    structured_llm = llm.with_structured_output(JobRequirements)

    result: JobRequirements = structured_llm.invoke(
        [
            ("system", _PARSE_JOB_SYSTEM_PROMPT),
            ("human", state["job_posting_raw"]),
        ]
    )

    job_requirements = result.model_dump()

    return {
        "job_requirements": job_requirements,
        "trajectory_log": log_step(
            state,
            node="parse_job",
            input_summary=state["job_posting_raw"][:200],
            output_summary=f"seniority={job_requirements['seniority']}, "
            f"{len(job_requirements['must_have_skills'])} must-have skills, "
            f"{len(job_requirements['keywords'])} keywords",
        ),
    }


_TAILOR_RESUME_SYSTEM_PROMPT = """Sos un asesor de carrera que adapta CVs a
vacantes específicas.

Reglas estrictas de fidelidad (NO NEGOCIABLES):
- NUNCA inventes experiencia, tecnologías, servicios específicos, fechas,
  métricas o logros que no estén literalmente en el CV original.
- Si el CV dice "AWS" a secas, escribí "AWS" — NO agregues servicios
  específicos como EC2, RDS, S3, etc. que el CV no menciona.
- NO agregues fechas a proyectos que no las tenían en el original.
- NO agregues herramientas, prácticas o procesos (ej: CI/CD, GitHub Actions,
  pipelines, testing frameworks) que no estén explícitamente mencionados.
- Antes de escribir cualquier tecnología, fecha o herramienta, verificá que
  puedas señalar exactamente dónde aparece en el CV original. Si no podés
  señalarla textualmente, NO la incluyas.
- Podés reordenar, resumir y enfatizar. NO podés agregar especificidad que
  el original no tiene.
- Si el CV no cubre alguna must_have_skill, no la agregues como si la
  tuviera: es información honesta que el humano revisor necesita ver.
- Devolvé el CV completo en formato markdown, con secciones claras
  (Resumen, Experiencia, Skills, Educación, Certificaciones).

Si recibís notas de revisión de una vuelta anterior, aplicá exactamente esos
cambios sobre el CV ya adaptado, sin rehacer todo desde cero."""


def tailor_resume(state: AgentState) -> dict:
    llm = ChatGroq(
        model=_MODEL_NAME,
        temperature=0.1,
        max_tokens=4096,
        model_kwargs={"reasoning_effort": "low"},
    )

    is_revision = bool(state.get("revision_notes"))

    if is_revision:
        human_message = (
            f"CV ya adaptado en la vuelta anterior:\n{state['tailored_cv']}\n\n"
            f"Notas de revisión del humano:\n{state['revision_notes']}\n\n"
            "Aplicá estos cambios y devolvé el CV completo actualizado."
        )
        input_summary = f"revisión: {state['revision_notes'][:200]}"
    else:
        human_message = (
            f"CV original:\n{state['cv_raw']}\n\n"
            f"Requisitos de la vacante (JSON):\n"
            f"{json.dumps(state['job_requirements'], ensure_ascii=False, indent=2)}"
        )
        input_summary = "primera adaptación del CV a la vacante"

    result = llm.invoke(
        [
            ("system", _TAILOR_RESUME_SYSTEM_PROMPT),
            ("human", human_message),
        ]
    )
    tailored_cv = result.content

    return {
        "tailored_cv": tailored_cv,
        # se resetean las notas: ya fueron aplicadas en esta vuelta
        "revision_notes": None,
        "trajectory_log": log_step(
            state,
            node="tailor_resume",
            input_summary=input_summary,
            output_summary=f"CV adaptado generado ({len(tailored_cv)} chars)",
        ),
    }


_GENERATE_COVER_LETTER_SYSTEM_PROMPT = """Sos un asesor de carrera que escribe
cartas de presentación profesionales.

Reglas estrictas de fidelidad (NO NEGOCIABLES):
- Basate únicamente en lo que dice literalmente el CV adaptado (tailored_cv).
  NUNCA inventes logros, tecnologías, servicios específicos, fechas o
  detalles que no estén ahí.
- Si el CV dice "AWS" a secas, NO digas que la experiencia "cubre" o
  "incluye" servicios específicos como EC2, RDS, S3, etc. Mencionar la
  vacante no te da permiso para asumir que el candidato tiene esa
  especificidad si el CV no la tiene.
- NO menciones CI/CD, pipelines, GitHub Actions, testing frameworks u
  otras prácticas/herramientas que no estén explícitamente en el CV
  adaptado, aunque la vacante las pida.
- No uses frases que "traduzcan" una skill genérica del CV en una
  específica de la vacante (ej: CV dice "AWS", vacante pide "RDS" → NO
  escribas que el candidato tiene experiencia en RDS).
- NO inventes motivación personal específica hacia la empresa (ej: "siempre
  soñé con trabajar aquí", "admiro profundamente su misión") — no tenés
  forma de saber eso y sería tan deshonesto como inventar experiencia. En
  su lugar, conectá objetivamente la experiencia real del candidato con lo
  que la vacante pide (role_summary y must_have_skills).
- Tono profesional, directo, sin relleno genérico ("soy una persona
  proactiva y comprometida" sin evidencia concreta que lo respalde).
- Extensión: 3-4 párrafos cortos. Sin encabezados de carta formal (fecha,
  dirección) — solo el cuerpo del texto.

Si recibís notas de revisión de una vuelta anterior, aplicá exactamente esos
cambios sobre la carta ya generada, sin rehacer todo desde cero."""


def generate_cover_letter(state: AgentState) -> dict:
    llm = ChatGroq(
        model=_MODEL_NAME,
        temperature=0.1,
        max_tokens=2048,
        model_kwargs={"reasoning_effort": "low"},
    )

    is_revision = bool(state.get("revision_notes"))

    if is_revision:
        human_message = (
            f"Carta generada en la vuelta anterior:\n{state['cover_letter']}\n\n"
            f"Notas de revisión del humano:\n{state['revision_notes']}\n\n"
            "Aplicá estos cambios y devolvé la carta completa actualizada."
        )
        input_summary = f"revisión: {state['revision_notes'][:200]}"
    else:
        human_message = (
            f"CV adaptado del candidato:\n{state['tailored_cv']}\n\n"
            f"Resumen del rol y requisitos (JSON):\n"
            f"{json.dumps(state['job_requirements'], ensure_ascii=False, indent=2)}"
        )
        input_summary = "primera generación de la carta"

    result = llm.invoke(
        [
            ("system", _GENERATE_COVER_LETTER_SYSTEM_PROMPT),
            ("human", human_message),
        ]
    )
    cover_letter = result.content

    return {
        "cover_letter": cover_letter,
        "revision_notes": None,
        "trajectory_log": log_step(
            state,
            node="generate_cover_letter",
            input_summary=input_summary,
            output_summary=f"Carta generada ({len(cover_letter)} chars)",
        ),
    }


_MAX_GROUNDING_RETRIES = 2


def verify_grounding(state: AgentState) -> dict:
    """Verificación determinística (sin LLM) de que el CV adaptado y la
    carta no contengan keywords de la vacante que no estaban en el CV
    original. Si un término solo aparece en el output y no en el CV real,
    solo pudo llegar ahí copiado de la vacante -> alucinación de
    especificidad, el mismo patrón que causó las alucinaciones de
    AWS/RDS/EC2/CI-CD documentadas en el changelog.
    """
    cv_lower = state["cv_raw"].lower()
    tailored_lower = (state.get("tailored_cv") or "").lower()
    letter_lower = (state.get("cover_letter") or "").lower()

    violations = []
    for keyword in state["job_requirements"].get("keywords", []):
        kw_lower = keyword.lower()
        if kw_lower in cv_lower:
            continue  # está genuinamente en el CV, no es alucinación
        if kw_lower in tailored_lower or kw_lower in letter_lower:
            violations.append(keyword)

    retries = state.get("grounding_retries", 0)
    grounded = len(violations) == 0
    should_retry = not grounded and retries < _MAX_GROUNDING_RETRIES

    revision_notes = None
    if should_retry:
        revision_notes = (
            "Verificación automática detectó términos que aparecen en el "
            "CV adaptado o la carta pero NO en el CV original: "
            f"{', '.join(violations)}. Estos términos vienen de la vacante, "
            "no del candidato. Remové o generalizá estas menciones "
            "(ej: si dijiste 'RDS' pero el CV solo tiene 'AWS', volvé a "
            "escribir 'AWS' a secas)."
        )

    return {
        "grounding_violations": violations,
        "grounding_retries": retries + 1 if should_retry else retries,
        "revision_notes": revision_notes,
        "trajectory_log": log_step(
            state,
            node="verify_grounding",
            input_summary=f"chequeando {len(state['job_requirements'].get('keywords', []))} keywords",
            output_summary=(
                "sin violaciones, grounding OK"
                if grounded
                else f"{len(violations)} violaciones detectadas: {violations} "
                f"({'reintentando' if should_retry else 'límite de reintentos alcanzado'})"
            ),
        ),
    }


def score_ats(state: AgentState) -> dict:
    # TODO: comparar state["tailored_cv"] contra state["job_requirements"]
    # y devolver {"ats_score": {"score": 0-100, "missing_keywords": [...]}}
    raise NotImplementedError


def human_checkpoint(state: AgentState) -> dict:
    # TODO: implementar con interrupt() de LangGraph para pausar el grafo
    # y esperar aprobación humana antes de finalize().
    raise NotImplementedError


def finalize(state: AgentState) -> dict:
    # TODO: armar el paquete final de salida (CV + carta + score + log)
    raise NotImplementedError