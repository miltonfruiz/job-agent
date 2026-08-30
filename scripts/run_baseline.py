"""
Corre el baseline (un solo prompt, sin herramientas) sobre todas las
vacantes en starter_materials/job_postings/, y calcula el mismo ATS score
que se usa para el agente (mismo cálculo, mismos requisitos parseados),
para que la comparación baseline vs. agente sea justa.

Uso:
    python scripts/run_baseline.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.baseline import run_baseline  # noqa: E402
from app.eval_utils import fabricated_skills, honest_must_have_coverage_pct  # noqa: E402
from app.graph.nodes import parse_job, score_ats  # noqa: E402

CV_PATH = Path("starter_materials/cvs/milton_cv.txt")
JOB_POSTINGS_DIR = Path("starter_materials/job_postings")
RESULTS_DIR = Path("trajectories/baseline")


def main():
    cv_raw = CV_PATH.read_text(encoding="utf-8")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for job_path in sorted(JOB_POSTINGS_DIR.glob("*.txt")):
        print(f"\n=== Baseline: {job_path.name} ===")
        job_posting_raw = job_path.read_text(encoding="utf-8")

        # parse_job acá NO es parte del baseline - es el criterio de
        # evaluación compartido, para scorear baseline y agente con
        # exactamente los mismos requisitos "ground truth".
        state = {"job_posting_raw": job_posting_raw, "trajectory_log": []}
        state.update(parse_job(state))

        baseline_result = run_baseline(job_posting_raw, cv_raw)
        state["tailored_cv"] = baseline_result["tailored_cv"]

        score_result = score_ats(state)
        score = score_result["ats_score"]

        fabricated = fabricated_skills(
            cv_raw,
            baseline_result["tailored_cv"],
            state["job_requirements"].get("must_have_skills", []),
        )
        honest_coverage = honest_must_have_coverage_pct(
            cv_raw,
            baseline_result["tailored_cv"],
            state["job_requirements"].get("must_have_skills", []),
        )

        print(
            f"Score bruto: {score['score']} "
            f"(must-have: {score['must_have_coverage_pct']}%, "
            f"keywords: {score['keyword_coverage_pct']}%)"
        )
        print(f"Cobertura HONESTA de must-have: {honest_coverage}%")
        print(f"Skills fabricadas (no están en el CV real): {fabricated}")

        entry = {
            "job_posting": job_path.name,
            "raw_output": baseline_result["raw_output"],
            "tailored_cv": baseline_result["tailored_cv"],
            "cover_letter": baseline_result["cover_letter"],
            "ats_score": score,
            "fabricated_skills": fabricated,
            "honest_must_have_coverage_pct": honest_coverage,
        }
        results.append(entry)

        out_path = RESULTS_DIR / f"{job_path.stem}.json"
        out_path.write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print("\n=== Resumen baseline (todas las vacantes) ===")
    for r in results:
        print(
            f"{r['job_posting']}: bruto={r['ats_score']['score']}, "
            f"honesto={r['honest_must_have_coverage_pct']}%, "
            f"fabricado={len(r['fabricated_skills'])} skills"
        )

    avg_score = sum(r["ats_score"]["score"] for r in results) / len(results)
    avg_honest = sum(r["honest_must_have_coverage_pct"] for r in results) / len(
        results
    )
    avg_fabricated = sum(len(r["fabricated_skills"]) for r in results) / len(results)
    print(f"\nScore BRUTO promedio del baseline: {avg_score:.1f}")
    print(f"Cobertura HONESTA promedio del baseline: {avg_honest:.1f}")
    print(f"Promedio de skills fabricadas por CV: {avg_fabricated:.1f}")


if __name__ == "__main__":
    main()