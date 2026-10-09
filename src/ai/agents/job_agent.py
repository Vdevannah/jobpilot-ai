"""A minimal agent for structured job analysis."""

from src.ai.client import LLMClient
from src.ai.job_analyzer import analyze_job_description
from src.ai.schemas import JobAnalysis


class JobAnalysisAgent:
    """Analyze descriptions using a caller-provided client."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def analyze(self, description: str) -> JobAnalysis:
        return analyze_job_description(description, self.client)
