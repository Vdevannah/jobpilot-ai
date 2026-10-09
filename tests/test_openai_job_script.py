import os
from unittest.mock import Mock

import pytest

from scripts import test_openai_job as script
from src.ai.schemas import JobAnalysis


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected network access")
    monkeypatch.setattr("socket.socket", forbidden)


def test_without_live_does_not_load_credentials_or_construct_client(monkeypatch, capsys):
    client = Mock()
    loader = Mock()
    monkeypatch.setattr(script, "OpenAIJobClient", client)
    monkeypatch.setattr(script, "load_dotenv", loader)

    assert script.main([]) == 0
    client.assert_not_called()
    loader.assert_not_called()
    assert "--live" in capsys.readouterr().out


@pytest.mark.parametrize("existing_model", [None, "environment-model"])
def test_root_environment_loading_and_mocked_analysis(
    monkeypatch, tmp_path, capsys, existing_model
):
    root = tmp_path / "project"
    root.mkdir()
    (root / ".env").write_text(
        "OPENAI_API_KEY=test-only-placeholder\nOPENAI_MODEL=file-model\n"
    )
    monkeypatch.setattr(script, "PROJECT_ROOT", root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    if existing_model:
        monkeypatch.setenv("OPENAI_MODEL", existing_model)
    analysis = JobAnalysis(
        required_skills=["medicinal chemistry"], preferred_skills=[],
        minimum_experience_years=8, job_track="pharma", summary="Test result.",
    )
    client = Mock()
    client.analyze_job.return_value = analysis

    def construct():
        assert os.environ["OPENAI_API_KEY"] == "test-only-placeholder"
        assert os.environ["OPENAI_MODEL"] == (existing_model or "file-model")
        return client

    monkeypatch.setattr(script, "OpenAIJobClient", construct)
    assert script.main(["--live"]) == 0
    client.analyze_job.assert_called_once_with(script.JOB_DESCRIPTION)
    output = capsys.readouterr().out
    assert output == analysis.model_dump_json(indent=2) + "\n"
    assert "test-only-placeholder" not in output


def test_client_error_has_nonzero_exit_without_exposing_details(monkeypatch, capsys):
    monkeypatch.setattr(script, "load_dotenv", Mock())
    monkeypatch.setattr(
        script, "OpenAIJobClient",
        Mock(side_effect=script.OpenAIJobClientError("private details")),
    )
    assert script.main(["--live"]) == 1
    output = capsys.readouterr()
    assert "failed" in output.err
    assert "private details" not in output.err
