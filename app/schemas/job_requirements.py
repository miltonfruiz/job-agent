from pydantic import BaseModel, Field


class JobRequirements(BaseModel):
    seniority: str = Field(description="Ej: junior, semi-senior, senior")
    must_have_skills: list[str] = Field(
        description="Skills o tecnologías explícitamente requeridas"
    )
    nice_to_have_skills: list[str] = Field(
        description="Skills mencionadas como deseables pero no obligatorias"
    )
    keywords: list[str] = Field(
        description="Términos clave que probablemente escanea un ATS "
        "(nombres de tecnologías, certificaciones, metodologías)"
    )
    role_summary: str = Field(
        description="Resumen de 1-2 líneas de qué hace el puesto"
    )
