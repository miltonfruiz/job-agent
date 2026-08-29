from langgraph.graph import StateGraph, END

from app.graph.state import AgentState
from app.graph.nodes import (
    parse_job,
    tailor_resume,
    generate_cover_letter,
    score_ats,
    human_checkpoint,
    finalize,
)


def route_after_checkpoint(state: AgentState) -> str:
    """Si el humano aprueba, cierra. Si no, vuelve a tailor_resume con notas."""
    if state.get("human_approved"):
        return "finalize"
    return "tailor_resume"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("parse_job", parse_job)
    graph.add_node("tailor_resume", tailor_resume)
    graph.add_node("generate_cover_letter", generate_cover_letter)
    graph.add_node("score_ats", score_ats)
    graph.add_node("human_checkpoint", human_checkpoint)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("parse_job")
    graph.add_edge("parse_job", "tailor_resume")
    graph.add_edge("tailor_resume", "generate_cover_letter")
    graph.add_edge("generate_cover_letter", "score_ats")
    graph.add_edge("score_ats", "human_checkpoint")

    graph.add_conditional_edges(
        "human_checkpoint",
        route_after_checkpoint,
        {"finalize": "finalize", "tailor_resume": "tailor_resume"},
    )
    graph.add_edge("finalize", END)

    return graph.compile()
