"""Resume analysis through an injected client."""

from src.ai.client import ResumeLLMClient
from src.ai.schemas import ResumeAnalysis


class ResumeAnalysisAgent:
    """Validate client output without inferring or combining experience."""

    def __init__(self, client: ResumeLLMClient) -> None:
        self.client = client

    def analyze(self, resume_text: str) -> ResumeAnalysis:
        if not resume_text.strip():
            raise ValueError("Resume text must not be empty or blank.")

        return ResumeAnalysis.model_validate(self.client.analyze_resume(resume_text))
