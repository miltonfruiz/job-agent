from typing import TypedDict, Optional


class AgentState(TypedDict):
    job_posting_raw: str
    cv_raw: str
    job_requirements: Optional[dict]
    tailored_cv: Optional[str]
    cover_letter: Optional[str]
    ats_score: Optional[dict]
    human_approved: Optional[bool]
    revision_notes: Optional[str]
    trajectory_log: list
