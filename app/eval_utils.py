"""
Funciones de evaluación compartidas entre scripts/run_baseline.py y
scripts/run_evaluation.py. Miden si un tailored_cv (venga del baseline o
del agente) es honesto respecto al CV real, no solo si "matchea" con la
vacante.
"""

from app.graph.nodes import _keyword_present


def fabricated_skills(cv_raw: str, tailored_cv: str, must_have: list) -> list:
    """Skills que el CV adaptado reclama pero que NO están en el CV real."""
    return [
        s
        for s in must_have
        if _keyword_present(s, tailored_cv) and not _keyword_present(s, cv_raw)
    ]


def honest_must_have_coverage_pct(
    cv_raw: str, tailored_cv: str, must_have: list
) -> float:
    """Cobertura real: solo cuenta must-have skills presentes TANTO en el
    CV adaptado como en el original."""
    if not must_have:
        return 100.0
    genuinely_matched = [
        s
        for s in must_have
        if _keyword_present(s, tailored_cv) and _keyword_present(s, cv_raw)
    ]
    return round(len(genuinely_matched) / len(must_have) * 100)