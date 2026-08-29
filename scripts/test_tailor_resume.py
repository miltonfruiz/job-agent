"""
Prueba manual del nodo tailor_resume usando archivos reales en vez de
texto pegado en la terminal.

Uso:
    python scripts/test_tailor_resume.py starter_materials/job_postings/job_01_backend_python.txt

Requiere que ya hayas corrido parse_job sobre la misma vacante, o corre
parse_job automáticamente si no le pasás job_requirements ya calculados.

Guarda el resultado en trajectories/ con timestamp, para tener evidencia
reproducible del entregable "agent trajectories".
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.graph.nodes import (  # noqa: E402
    parse_job,
    tailor_resume,
    generate_cover_letter,
    verify_grounding,
)

CV_PATH = Path("starter_materials/cvs/milton_cv.txt")
TRAJECTORIES_DIR = Path("trajectories")


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/test_tailor_resume.py <path_a_vacante.txt>")
        sys.exit(1)

    job_path = Path(sys.argv[1])
    job_posting_raw = job_path.read_text(encoding="utf-8")
    cv_raw = CV_PATH.read_text(encoding="utf-8")

    state = {
        "job_posting_raw": job_posting_raw,
        "cv_raw": cv_raw,
        "trajectory_log": [],
    }

    print(f"--- Parseando vacante: {job_path.name} ---")
    parse_result = parse_job(state)
    state.update(parse_result)
    print(json.dumps(state["job_requirements"], ensure_ascii=False, indent=2))

    print("\n--- Adaptando CV ---")
    tailor_result = tailor_resume(state)
    state.update(tailor_result)
    print(state["tailored_cv"])

    print("\n--- Generando carta de presentación ---")
    letter_result = generate_cover_letter(state)
    state.update(letter_result)
    print(state["cover_letter"])

    state.setdefault("grounding_retries", 0)
    print("\n--- Verificando grounding ---")
    for attempt in range(3):  # 1 chequeo inicial + hasta 2 reintentos
        grounding_result = verify_grounding(state)
        state.update(grounding_result)
        print(f"Violaciones: {state['grounding_violations']}")

        if not state.get("revision_notes"):
            print("Grounding OK, sin alucinaciones detectadas.")
            break

        print(f"Reintentando (vuelta {attempt + 1})...")
        state.update(tailor_resume(state))
        state.update(generate_cover_letter(state))
        print("--- CV re-adaptado ---")
        print(state["tailored_cv"])
        print("--- Carta regenerada ---")
        print(state["cover_letter"])

    TRAJECTORIES_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = TRAJECTORIES_DIR / f"tailor_resume_{job_path.stem}_{timestamp}.json"
    out_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nGuardado en {out_path}")


if __name__ == "__main__":
    main()