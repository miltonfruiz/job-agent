"""
Prueba del grafo completo (parse_job -> ... -> human_checkpoint -> finalize),
incluyendo el checkpoint humano real con interrupt()/resume de LangGraph.

A diferencia de scripts/test_tailor_resume.py (que llama funciones sueltas),
este script corre el grafo compilado de punta a punta, que es la única forma
en que interrupt() funciona correctamente.

Uso:
    python scripts/test_full_graph.py starter_materials/job_postings/job_01_fullstack.txt
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.types import Command  # noqa: E402

from app.graph.graph import build_graph  # noqa: E402

CV_PATH = Path("starter_materials/cvs/milton_cv.txt")


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/test_full_graph.py <path_a_vacante.txt>")
        sys.exit(1)

    job_path = Path(sys.argv[1])
    job_posting_raw = job_path.read_text(encoding="utf-8")
    cv_raw = CV_PATH.read_text(encoding="utf-8")

    graph = build_graph()
    # thread_id identifica esta "conversación" con el grafo, necesario para
    # que el checkpointer sepa qué ejecución reanudar después del interrupt.
    config = {"configurable": {"thread_id": f"test-{job_path.stem}"}}

    initial_state = {
        "job_posting_raw": job_posting_raw,
        "cv_raw": cv_raw,
        "trajectory_log": [],
        "grounding_retries": 0,
    }

    print("--- Corriendo el grafo hasta el checkpoint humano ---")
    result = graph.invoke(initial_state, config=config)

    if "__interrupt__" not in result:
        print("El grafo terminó sin pasar por el checkpoint (revisar lógica).")
        print("\n--- DIAGNÓSTICO ---")
        print("Claves del resultado:", list(result.keys()))
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return

    # Loop: puede haber más de una vuelta de revisión si pedís cambios
    # más de una vez. Se repite hasta que apruebes o LangGraph termine.
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("\n>>> CHECKPOINT HUMANO <<<")
        print(payload["message"])
        print("\n--- CV adaptado ---")
        print(payload["tailored_cv"])
        print("\n--- Carta ---")
        print(payload["cover_letter"])
        print("\n--- ATS score ---")
        print(json.dumps(payload["ats_score"], ensure_ascii=False, indent=2))

        respuesta = input(
            "\n¿Aprobás esta aplicación? (s = sí / cualquier otra cosa = "
            "pedir cambios): "
        )

        if respuesta.strip().lower() in ("s", "si", "sí", "y", "yes"):
            resume_value = {"approved": True}
        else:
            notes = input("¿Qué querés que cambie?: ")
            resume_value = {"approved": False, "notes": notes}

        print("\n--- Reanudando el grafo con tu decisión ---")
        result = graph.invoke(Command(resume=resume_value), config=config)

    trajectories_dir = Path("trajectories")
    trajectories_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = trajectories_dir / f"full_graph_{job_path.stem}_{timestamp}.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nTrayectoria completa (incluye human_checkpoint) guardada en {out_path}")
    print("\n--- Resultado final ---")
    print(json.dumps(result["ats_score"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()