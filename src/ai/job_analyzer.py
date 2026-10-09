"""Analyze job descriptions through an injected client."""

from src.ai.client import LLMClient
from src.ai.schemas import JobAnalysis


def analyze_job_description(description: str, client: LLMClient) -> JobAnalysis:
    """Reject blank input and validate client output, raising ValidationError if invalid."""
    if not description.strip():
        raise ValueError("Job description must not be empty or blank.")

    return JobAnalysis.model_validate(client.analyze_job(description))
