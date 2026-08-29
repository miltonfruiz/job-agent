"""
Cada función es un nodo del grafo. Reciben y devuelven un dict parcial
que LangGraph mergea sobre el AgentState.

Convención: cada nodo apendea un entry a trajectory_log con
{node, input_summary, output_summary, timestamp} para el entregable
de "agent trajectories" del hackathon.
"""

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


def tailor_resume(state: AgentState) -> dict:
    # TODO: usar state["job_requirements"] + state["cv_raw"] (o
    # state["tailored_cv"] + state["revision_notes"] si viene de un loop
    # de revisión) para reescribir el CV.
    raise NotImplementedError


def generate_cover_letter(state: AgentState) -> dict:
    # TODO: usar state["job_requirements"] + state["tailored_cv"]
    raise NotImplementedError


def score_ats(state: AgentState) -> dict:
    # TODO: comparar state["tailored_cv"] contra state["job_requirements"]
    # y devolver {"ats_score": {"score": 0-100, "missing_keywords": [...]}}
    # Esto funciona como verificación automática antes del checkpoint humano.
    raise NotImplementedError


def human_checkpoint(state: AgentState) -> dict:
    # TODO: implementar con interrupt() de LangGraph para pausar el grafo
    # y esperar aprobación humana antes de finalize().
    raise NotImplementedError


def finalize(state: AgentState) -> dict:
    # TODO: armar el paquete final de salida (CV + carta + score + log)
    raise NotImplementedError