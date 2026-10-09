"""Phase 7G.5J: deterministic Scientific AI / Cheminformatics recognition.

All fictional synthetic text; this module never reads resume content,
CandidateProfile, or the separate job-discovery matching engine.
"""
import pytest

from src.ai.job_track_classifier import classify_scientific_ai


def classify(required=(), preferred=(), summary=''):
    return classify_scientific_ai(list(required), list(preferred), summary)


# --- true positives: meaningful combinations ---

def test_cheminformatics_role_recognized():
    assert classify(
        required=['cheminformatics', 'RDKit'],
        summary='Fictional Cheminformatics Scientist building molecular ML models.',
    )


def test_ai_drug_discovery_role_recognized():
    assert classify(
        required=['AI-driven drug discovery', 'Python'],
        summary='Fictional Research Scientist applying AI to drug discovery pipelines.',
    )


def test_molecular_property_prediction_role_recognized():
    assert classify(
        required=['molecular property prediction', 'machine learning'],
        summary='Fictional Scientist predicting molecular properties with ML models.',
    )


def test_computational_chemistry_plus_machine_learning_recognized():
    assert classify(
        required=['computational chemistry', 'machine learning'],
        summary='Fictional computational chemist applying machine learning to molecular design.',
    )


def test_ai_driven_medicinal_chemistry_recognized():
    assert classify(
        summary='Fictional AI-driven medicinal chemistry role using generative models.',
    )


# --- preserved classifications: must NOT trigger scientific_ai ---

def test_conventional_medicinal_chemistry_not_recognized():
    assert not classify(
        required=['SAR', 'PROTACs', 'structure-based drug design'],
        preferred=['oncology'],
        summary='Fictional Principal Scientist, Medicinal Chemistry, 8 years pharmaceutical research.',
    )


def test_synthetic_chemistry_not_recognized():
    assert not classify(
        required=['organic synthesis', 'purification', 'characterization'],
        summary='Fictional Synthetic Chemist responsible for multi-step organic synthesis of novel compounds.',
    )


def test_general_data_engineering_not_recognized():
    assert not classify(
        required=['Python', 'SQL', 'ETL pipelines', 'Spark'],
        summary='Fictional Data Engineer building ETL pipelines, 3 years experience.',
    )


def test_general_data_science_not_recognized():
    assert not classify(
        required=['machine learning', 'Python', 'statistics'],
        summary='Fictional Data Scientist running A/B tests and building ML models for marketing.',
    )


def test_business_analyst_not_recognized():
    assert not classify(
        required=['SQL', 'stakeholder management', 'dashboards'],
        summary='Fictional Business Analyst producing reporting dashboards for leadership.',
    )


# --- individual generic terms alone must never trigger a match ---

@pytest.mark.parametrize('summary', [
    'Fictional role requiring Python scripting.',
    'Fictional role requiring AI experience.',
    'Fictional role in chemistry.',
    'Fictional role in data science.',
])
def test_single_generic_term_alone_not_recognized(summary):
    assert not classify(summary=summary)


# --- ambiguous / hybrid roles stay unresolved, not forced to a track ---

def test_ambiguous_pharma_data_hybrid_not_forced_to_scientific_ai():
    assert not classify(
        required=['medicinal chemistry', 'machine learning'],
        summary=(
            'Fictional hybrid role combining medicinal chemistry bench work with '
            'machine learning model development; final track classification unclear.'
        ),
    )


def test_ambiguous_role_with_only_juxtaposed_terms_not_recognized():
    # Chemistry and data-science terms mentioned separately, not as an
    # explicit combined discipline, must not force a confident classification.
    assert not classify(
        required=['chemistry degree', 'data science coursework'],
        summary='Fictional role for a chemistry graduate interested in data science.',
    )


# --- no professional-experience inference of any kind ---

def test_classifier_has_no_resume_or_profile_imports():
    from src.ai import job_track_classifier
    assert not hasattr(job_track_classifier, 'ResumeAnalysis')
    assert not hasattr(job_track_classifier, 'CandidateProfile')
    assert classify_scientific_ai.__code__.co_names.count('professional_experience_years') == 0
