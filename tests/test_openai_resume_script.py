import pytest
from unittest.mock import Mock

from scripts import test_openai_resume as script
from src.ai.schemas import ResumeAnalysis


def test_without_live_never_constructs_client_or_loads_environment(monkeypatch, capsys):
    factory, loader = Mock(), Mock()
    monkeypatch.setattr(script, "OpenAIResumeClient", factory)
    monkeypatch.setattr(script, "load_dotenv", loader)
    assert script.main([]) == 0
    factory.assert_not_called()
    loader.assert_not_called()
    assert "--live" in capsys.readouterr().out


def test_live_path_with_fake_client_only(monkeypatch, capsys):
    loader, factory = Mock(), Mock()
    monkeypatch.setattr(script, "load_dotenv", loader)
    monkeypatch.setattr(script, "OpenAIResumeClient", factory)
    result = ResumeAnalysis(
        skills=[], professional_experience_years={"pharma": 8.0},
        domains=[], education=["PhD in Organic Chemistry"], summary="Test output",
    )
    factory.return_value.analyze_resume.return_value = result
    assert script.main(["--live"]) == 0
    loader.assert_called_once_with(script.PROJECT_ROOT / ".env", override=False)
    factory.return_value.analyze_resume.assert_called_once()
    assert "FICTIONAL SAMPLE" in script.SAMPLE_RESUME
    assert "No professional data engineering employment" in script.SAMPLE_RESUME
    assert capsys.readouterr().out.endswith(result.model_dump_json(indent=2) + "\n")


@pytest.fixture(autouse=True)
def approve_synthetic_preview(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "APPROVE")
