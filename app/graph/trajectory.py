from datetime import datetime, timezone


def log_step(state: dict, node: str, input_summary: str, output_summary: str) -> list:
    """Devuelve el trajectory_log actualizado con un nuevo entry.

    Se usa en cada nodo para dejar registro de qué hizo el agente en ese paso,
    insumo directo para el entregable 'agent trajectories' del hackathon.
    """
    entry = {
        "node": node,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_summary": input_summary,
        "output_summary": output_summary,
    }
    return state.get("trajectory_log", []) + [entry]
