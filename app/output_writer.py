"""
Guarda el paquete final ya aprobado por el humano como archivos limpios y
legibles (Markdown), en vez de dejarlo solo en un JSON de trayectoria que
hay que leer con código. Esto es lo que un usuario real revisaría y
enviaría - el resultado "que firmaría", como pide el criterio de
End-to-End Quality del hackathon.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUTS_DIR = Path("outputs")


def save_final_package(
    job_stem: str, tailored_cv: str, cover_letter: str, ats_score: dict
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package_dir = OUTPUTS_DIR / f"{job_stem}_{timestamp}"
    package_dir.mkdir(parents=True, exist_ok=True)

    (package_dir / "CV.md").write_text(tailored_cv, encoding="utf-8")
    (package_dir / "cover_letter.md").write_text(cover_letter, encoding="utf-8")
    (package_dir / "ats_score.json").write_text(
        json.dumps(ats_score, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return package_dir