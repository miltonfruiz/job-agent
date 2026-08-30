# Evaluación: Baseline vs. Agente

Mismo caso, mismo CV real, misma métrica de honestidad para ambos.

| Vacante | Agente (score) | Agente (fabricado) | Baseline (cobertura honesta) | Baseline (fabricado) |
|---|---|---|---|---|
| job_01_fullstack.txt | 53% | 0 | 54% | 11 |
| job_02_software_engineer.txt | 42% | 0 | 50% | 3 |
| job_03_frontend.txt | 27% | 0 | 33% | 15 |
| **Promedio** | **40.7%** | **0.0** | **45.7%** | **9.7** |

El score del agente ya es honesto por diseño (pasó por `verify_grounding` antes de llegar al humano). El score del baseline sin ajustar suele ser más alto en apariencia, pero solo porque inventa skills - la columna de cobertura honesta muestra la verdad de fondo, que en la práctica es similar a la del agente. La diferencia real no es cuánto matchea, es cuánto de eso es cierto.