"""
Cada función es un nodo del grafo. Reciben y devuelven un dict parcial
que LangGraph mergea sobre el AgentState.

Convención: cada nodo apendea un entry a trajectory_log con
{node, input_summary, output_summary, timestamp} para el entregable
de "agent trajectories" del hackathon.
"""

import json
import os
import re
import time

import app.config  # noqa: F401  (carga las variables de .env como side effect)
from groq import RateLimitError
from langchain_groq import ChatGroq
from langgraph.types import interrupt

from app.graph.state import AgentState
from app.graph.trajectory import log_step
from app.schemas.job_requirements import JobRequirements

_MAX_RATE_LIMIT_RETRIES = 4


def _invoke_with_retry(runnable, messages):
    """Groq (capa gratuita) limita a 8000 tokens/minuto. Si el pipeline
    corre varios nodos seguidos en poco tiempo (como en un run completo del
    grafo), es fácil pisar ese límite. Reintenta con backoff exponencial en
    vez de fallar todo el pipeline por un 429 transitorio.
    """
    last_error = None
    for attempt in range(_MAX_RATE_LIMIT_RETRIES):
        try:
            return runnable.invoke(messages)
        except RateLimitError as e:
            last_error = e
            wait_seconds = 2**attempt  # 1, 2, 4, 8 segundos
            time.sleep(wait_seconds)
    raise last_error

# Modelo rápido para iterar durante el desarrollo. Groq deprecó los modelos
# Llama (llama-3.1-8b-instant / llama-3.3-70b-versatile) en agosto 2026;
# gpt-oss-20b es el reemplazo recomendado para uso rápido/económico.
# Evaluar al final del hackathon si openai/gpt-oss-120b mejora el score ATS
# lo suficiente como para justificar la latencia extra en la solución
# "avanzada" (ver docs/CHANGELOG.md).
# Configurable por variable de entorno GROQ_MODEL, para poder cambiar de
# modelo sin tocar código si Groq agota el cupo diario de uno en particular
# (nos pasó durante el desarrollo: ver docs/REPRODUCTION.md).
_MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
# Los modelos GPT-OSS aceptan "low"/"medium"/"high"; otros modelos (ej.
# qwen) solo aceptan "none"/"default" - configurable por si hace falta
# cambiar de modelo (ver GROQ_MODEL arriba).
_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "low")

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

    result: JobRequirements = _invoke_with_retry(
        structured_llm,
        [
            ("system", _PARSE_JOB_SYSTEM_PROMPT),
            ("human", state["job_posting_raw"]),
        ],
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
        model_kwargs={"reasoning_effort": _REASONING_EFFORT},
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

    result = _invoke_with_retry(
        llm,
        [
            ("system", _TAILOR_RESUME_SYSTEM_PROMPT),
            ("human", human_message),
        ],
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
        model_kwargs={"reasoning_effort": _REASONING_EFFORT},
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

    result = _invoke_with_retry(
        llm,
        [
            ("system", _GENERATE_COVER_LETTER_SYSTEM_PROMPT),
            ("human", human_message),
        ],
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


_GENERIC_SUFFIX_WORDS = {"js", "css", "server", "framework"}


def _keyword_present(term: str, text: str) -> bool:
    """Compara si `term` está presente en `text`, tolerando variantes de
    términos compuestos (ej: CV dice "Node", vacante pide "Node.js") sin
    generar falsos positivos con palabras genéricas embebidas (ej: "SQL"
    dentro de "PostgreSQL" no debe contar como match de "SQL Server").

    Estrategia: primero intenta la frase exacta. Si no matchea, separa el
    término en palabras, descarta sufijos genéricos (js, css, server...) y
    busca la(s) palabra(s) núcleo restante(s) como palabra completa
    (con límites de palabra, \\b) en el texto.
    """
    term_lower = term.lower()
    text_lower = text.lower()

    if term_lower in text_lower:
        return True

    tokens = re.findall(r"[a-z0-9+]+", term_lower)
    core_tokens = [t for t in tokens if t not in _GENERIC_SUFFIX_WORDS] or tokens

    return any(
        re.search(rf"\b{re.escape(tok)}\b", text_lower) for tok in core_tokens
    )


_MAX_GROUNDING_RETRIES = 2


def verify_grounding(state: AgentState) -> dict:
    """Verificación determinística (sin LLM) de que el CV adaptado y la
    carta no contengan keywords de la vacante que no estaban en el CV
    original. Si un término solo aparece en el output y no en el CV real,
    solo pudo llegar ahí copiado de la vacante -> alucinación de
    especificidad, el mismo patrón que causó las alucinaciones de
    AWS/RDS/EC2/CI-CD documentadas en el changelog.
    """
    cv_raw = state["cv_raw"]
    tailored_cv = state.get("tailored_cv") or ""
    cover_letter = state.get("cover_letter") or ""

    violations = []
    for keyword in state["job_requirements"].get("keywords", []):
        if _keyword_present(keyword, cv_raw):
            continue  # está genuinamente en el CV, no es alucinación
        if _keyword_present(keyword, tailored_cv) or _keyword_present(
            keyword, cover_letter
        ):
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
    """Scoring determinístico (sin LLM) de qué tan bien tailored_cv cubre
    los requisitos de la vacante. Sirve como verificación automática antes
    del checkpoint humano, y como métrica objetiva y reproducible para
    comparar baseline vs. agente (mismo cálculo en ambos casos).
    """
    tailored_cv = state.get("tailored_cv") or ""
    must_have = state["job_requirements"].get("must_have_skills", [])
    keywords = state["job_requirements"].get("keywords", [])

    matched_must_have = [s for s in must_have if _keyword_present(s, tailored_cv)]
    missing_must_have = [s for s in must_have if not _keyword_present(s, tailored_cv)]
    matched_keywords = [k for k in keywords if _keyword_present(k, tailored_cv)]
    missing_keywords = [k for k in keywords if not _keyword_present(k, tailored_cv)]

    # Las must-have pesan más que el resto de las keywords: son lo que un
    # ATS real suele usar como filtro duro, no solo como ranking.
    must_have_coverage = len(matched_must_have) / len(must_have) if must_have else 1.0
    keyword_coverage = len(matched_keywords) / len(keywords) if keywords else 1.0
    score = round((0.7 * must_have_coverage + 0.3 * keyword_coverage) * 100)

    ats_score = {
        "score": score,
        "must_have_coverage_pct": round(must_have_coverage * 100),
        "keyword_coverage_pct": round(keyword_coverage * 100),
        "missing_must_have": missing_must_have,
        "missing_keywords": missing_keywords,
    }

    return {
        "ats_score": ats_score,
        "trajectory_log": log_step(
            state,
            node="score_ats",
            input_summary=f"{len(must_have)} must-have skills, {len(keywords)} keywords",
            output_summary=f"score={score}, faltan {len(missing_must_have)} "
            f"must-have skills: {missing_must_have}",
        ),
    }


def human_checkpoint(state: AgentState) -> dict:
    """Pausa el grafo y muestra CV adaptado + carta + score ATS juntos para
    una única aprobación humana, cumpliendo la regla del hackathon de que
    toda acción consecuente (acá: dar por lista una aplicación) requiere
    aprobación humana antes de ejecutarse.

    Usa interrupt() de LangGraph: la ejecución se detiene acá y devuelve el
    control a quien invocó el grafo. Para continuar, se vuelve a invocar el
    grafo con Command(resume=<respuesta del humano>).

    La respuesta esperada del humano es un dict:
        {"approved": True}
        o
        {"approved": False, "notes": "texto con lo que hay que cambiar"}
    """
    human_response = interrupt(
        {
            "tailored_cv": state.get("tailored_cv"),
            "cover_letter": state.get("cover_letter"),
            "ats_score": state.get("ats_score"),
            "grounding_violations": state.get("grounding_violations"),
            "message": "Revisá el CV, la carta y el score ATS. ¿Aprobás "
            "esta aplicación tal como está, o pedís cambios?",
        }
    )

    approved = bool(human_response.get("approved"))
    notes = human_response.get("notes") if not approved else None

    return {
        "human_approved": approved,
        "revision_notes": notes,
        "trajectory_log": log_step(
            state,
            node="human_checkpoint",
            input_summary=f"ats_score={state.get('ats_score', {}).get('score')}",
            output_summary="aprobado" if approved else f"revisión pedida: {notes}",
        ),
    }


def finalize(state: AgentState) -> dict:
    """Cierra el grafo una vez aprobado por el humano. El paquete final ya
    está armado en el state (tailored_cv, cover_letter, ats_score) — este
    nodo solo deja registro de que la aplicación quedó lista, para que
    quien invoque el grafo desde afuera (API o script) sepa que puede
    guardar/entregar el resultado.
    """
    return {
        "trajectory_log": log_step(
            state,
            node="finalize",
            input_summary="aplicación aprobada por el humano",
            output_summary=f"paquete final listo, ats_score="
            f"{state.get('ats_score', {}).get('score')}",
        ),
    }