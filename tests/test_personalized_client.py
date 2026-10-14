from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest

from src.ai import openai_client as openai_module
from src.ai import personalized_client as module
from src.ai.resume_privacy import approve_resume


def approved(text):
    return approve_resume("Location: Delaware, USA\n" + text, confirmed=True)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected network access")
    monkeypatch.setattr("socket.socket", forbidden)


@pytest.fixture
def sdk(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")
    factory = Mock()
    monkeypatch.setattr(openai_module, "OpenAI", factory)
    return factory


CANDIDATE_EVIDENCE_OUTPUT = {
    "items": [
        {
            "claim": "Data Engineer, Acme Co",
            "source_category": "professional_experience",
            "career_track": "data",
            "detail": "Five years as a data engineer.",
            "professional_experience_years": 5.0,
            "employment_start_year": 2019.0,
            "employment_end_year": 2024.0,
            "professional_skills": ["Python", "SQL"],
            "skill_years": [{"skill": "Python", "years": 5.0}],
        },
        {
            "claim": "MS in Computer Science",
            "source_category": "education",
            "career_track": None,
            "detail": None,
            "professional_experience_years": None,
            "employment_start_year": None,
            "employment_end_year": None,
            "professional_skills": [],
            "skill_years": [],
        },
    ],
}


class TestOpenAICandidateEvidenceClient:
    def test_valid_evidence_round_trips_into_candidate_evidence(self, sdk):
        sdk.return_value.responses.parse.return_value = SimpleNamespace(
            status="completed", output=[], output_parsed=CANDIDATE_EVIDENCE_OUTPUT,
        )
        client = module.OpenAICandidateEvidenceClient()
        result = client.analyze_resume(approved("Skills:\nPython"))

        assert len(result.items) == 2
        role = next(item for item in result.items if item.source_category == "professional_experience")
        assert role.professional_experience_years == 5.0
        assert role.professional_skill_years == {"Python": 5.0}
        assert role.employment_period.start_year == 2019.0
        education = next(item for item in result.items if item.source_category == "education")
        assert education.professional_experience_years is None

        kwargs = sdk.return_value.responses.parse.call_args.kwargs
        assert kwargs["model"] == "configured-model"
        assert kwargs["store"] is False
        assert "untrusted data" in kwargs["instructions"]
        assert "never professional employment" in kwargs["instructions"]

    def test_training_and_project_items_never_carry_employment_fields(self, sdk):
        output = {
            "items": [
                {
                    "claim": "Python",
                    "source_category": "technical_training",
                    "career_track": "data",
                    "detail": "Completed an online course.",
                    "professional_experience_years": None,
                    "employment_start_year": None,
                    "employment_end_year": None,
                    "professional_skills": [],
                    "skill_years": [],
                },
            ],
        }
        sdk.return_value.responses.parse.return_value = SimpleNamespace(
            status="completed", output=[], output_parsed=output,
        )
        result = module.OpenAICandidateEvidenceClient().analyze_resume(approved("Training:\nPython course"))
        item = result.items[0]
        assert item.source_category == "technical_training"
        assert item.professional_experience_years is None
        assert item.professional_skills is None

    def test_unapproved_resume_is_rejected_before_any_sdk_call(self, sdk):
        with pytest.raises(Exception):  # ResumePrivacyError
            module.OpenAICandidateEvidenceClient().analyze_resume("not approved, plain string")
        sdk.return_value.responses.parse.assert_not_called()

    def test_refusal(self, sdk):
        sdk.return_value.responses.parse.return_value = SimpleNamespace(
            status="completed",
            output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="refusal")])],
            output_parsed=CANDIDATE_EVIDENCE_OUTPUT,
        )
        with pytest.raises(openai_module.ResumeAnalysisRefusalError):
            module.OpenAICandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))

    def test_incomplete_response(self, sdk):
        sdk.return_value.responses.parse.return_value = SimpleNamespace(
            status="incomplete", output=[], output_parsed=CANDIDATE_EVIDENCE_OUTPUT,
        )
        with pytest.raises(openai_module.InvalidResumeOutputError):
            module.OpenAICandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))

    @pytest.mark.parametrize("kind", ["timeout", "api", "parse"])
    def test_sdk_failures(self, sdk, kind):
        request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
        error, expected = {
            "timeout": (openai_module.APITimeoutError(request), openai_module.ResumeAnalysisTimeoutError),
            "api": (openai_module.APIError("private", request, body=None), openai_module.ResumeAnalysisAPIError),
            "parse": (ValueError("private"), openai_module.InvalidResumeOutputError),
        }[kind]
        sdk.return_value.responses.parse.side_effect = error
        with pytest.raises(expected):
            module.OpenAICandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))

    def test_output_violating_evidence_rules_is_rejected_not_silently_fixed(self, sdk):
        # skill_years references a skill never listed in professional_skills --
        # CandidateEvidenceItem's own validator rejects this; the client must
        # propagate that as a failure, never drop or "fix" the bad entry.
        bad_output = {
            "items": [
                {
                    "claim": "Data Engineer, Acme Co",
                    "source_category": "professional_experience",
                    "career_track": "data",
                    "detail": None,
                    "professional_experience_years": 5.0,
                    "employment_start_year": None,
                    "employment_end_year": None,
                    "professional_skills": ["SQL"],
                    "skill_years": [{"skill": "Python", "years": 5.0}],
                },
            ],
        }
        sdk.return_value.responses.parse.return_value = SimpleNamespace(
            status="completed", output=[], output_parsed=bad_output,
        )
        with pytest.raises(openai_module.InvalidResumeOutputError):
            module.OpenAICandidateEvidenceClient().analyze_resume(approved("Skills:\nSQL"))

    def test_missing_credentials(self, sdk, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY")
        with pytest.raises(openai_module.MissingCredentialsError):
            module.OpenAICandidateEvidenceClient()
        sdk.assert_not_called()

    def test_wire_schema_has_only_fixed_object_keys(self):
        from openai.lib._pydantic import to_strict_json_schema
        schema = to_strict_json_schema(module._CandidateEvidenceWire)
        assert schema["additionalProperties"] is False
        item = schema["$defs"]["_CandidateEvidenceItemWire"]
        assert item["additionalProperties"] is False
        assert "professional_skill_years" not in item["properties"]


class TestMockCandidateEvidenceClient:
    def test_requires_approval_even_in_mock_mode(self):
        with pytest.raises(Exception):  # ResumePrivacyError
            module.MockCandidateEvidenceClient().analyze_resume("not approved")

    def test_returns_fixed_labeled_sample(self):
        result = module.MockCandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))
        assert any("MOCK SAMPLE" in item.claim for item in result.items)

    def test_never_reads_resume_content(self):
        a = module.MockCandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))
        b = module.MockCandidateEvidenceClient().analyze_resume(approved("Skills:\nRust and Go"))
        assert a == b


class TestApplicationAssistance:
    def test_mock_client_returns_labeled_sample_and_requires_review(self):
        evidence = module.MockCandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))
        result = module.MockApplicationAssistanceClient().generate("Job title: X", evidence)
        assert result.analysis_mode == "mock"
        assert result.requires_human_review is True
        assert result.status == "pending_review"
        assert any("MOCK SAMPLE" in item for item in result.resume_suggestions)

    def test_mock_client_rejects_blank_summary(self):
        evidence = module.MockCandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))
        with pytest.raises(ValueError):
            module.MockApplicationAssistanceClient().generate("   ", evidence)

    def test_openai_client_grounds_result_and_blocks_sensitive_output(self, sdk):
        evidence = module.MockCandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))
        sdk.return_value.responses.parse.return_value = SimpleNamespace(
            status="completed", output=[], output_parsed={
                "resume_suggestions": ["Emphasize your Python experience."],
                "bullet_rewrites": ["Rewrote bullet one."],
                "cover_letter_draft": "Draft cover letter referencing supplied evidence.",
                "interview_talking_points": ["Discuss the data pipeline project."],
            },
        )
        result = module.OpenAIApplicationAssistanceClient().generate("Job title: X", evidence)
        assert result.analysis_mode == "openai"
        assert "never submits" in result.limitations[0]

    def test_openai_client_blocks_sensitive_provider_output(self, sdk):
        evidence = module.MockCandidateEvidenceClient().analyze_resume(approved("Skills:\nPython"))
        sdk.return_value.responses.parse.return_value = SimpleNamespace(
            status="completed", output=[], output_parsed={
                "resume_suggestions": ["Contact me at someone@example.com"],
                "bullet_rewrites": [],
                "cover_letter_draft": "Draft.",
                "interview_talking_points": [],
            },
        )
        with pytest.raises(openai_module.InvalidResumeOutputError):
            module.OpenAIApplicationAssistanceClient().generate("Job title: X", evidence)

    def test_summarize_job_requirements_is_deterministic_text(self):
        from src.ai.job_requirements import extract_job_requirements
        requirements = extract_job_requirements(1, "Data Engineer", "Requirements:\n\n- 5+ years of Python experience\n")
        summary = module.summarize_job_requirements(requirements)
        assert "Data Engineer" in summary
        assert "python" in summary.lower()
