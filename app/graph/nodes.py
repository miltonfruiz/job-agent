"""
Cada función es un nodo del grafo. Reciben y devuelven un dict parcial
que LangGraph mergea sobre el AgentState.

Convención: cada nodo apendea un entry a trajectory_log con
{node, input_summary, output_summary, timestamp} para el entregable
de "agent trajectories" del hackathon.
"""

from app.graph.state import AgentState


def parse_job(state: AgentState) -> dict:
    # TODO: llamar a Groq para extraer requisitos, skills clave y seniority
    # a partir de state["job_posting_raw"]. Devolver algo como:
    # {"job_requirements": {"skills": [...], "seniority": "...", "keywords": [...]}}
    raise NotImplementedError


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
