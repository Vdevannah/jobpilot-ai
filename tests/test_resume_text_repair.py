import pytest

from src.ai.resume_privacy import ResumePrivacyError, approve_resume, preview_resume
from src.ai.resume_text_repair import (
    EDUCATION,
    EXPERIENCE,
    PROJECTS,
    PUBLICATIONS,
    QUALIFICATIONS,
    SKILLS,
    repair_section_headings,
)


def test_standalone_known_headings_are_normalized_to_canonical_labels():
    text = (
        'Professional Summary\n'
        'Fictional candidate with research background.\n'
        'Technical Skills\n'
        'FictionalLang, FictionalTool\n'
        'Employment History\n'
        'Fictional Corp, Fictional Scientist, 2015-2020\n'
        'Education\n'
        'PhD in Fictional Science, Fictional University\n'
        'Projects\n'
        'Fictional open-source fictional-parser\n'
    )
    result = repair_section_headings(text)
    lines = result.text.splitlines()
    assert QUALIFICATIONS in lines
    assert SKILLS in lines
    assert EXPERIENCE in lines
    assert EDUCATION in lines
    assert PROJECTS in lines
    assert result.report.mapped_headings == [QUALIFICATIONS, SKILLS, EXPERIENCE, EDUCATION, PROJECTS]
    assert result.report.ambiguous_count == 0
    assert result.report.unmapped_headings == []
    # All substantive content preserved verbatim.
    assert 'Fictional candidate with research background.' in result.text
    assert 'FictionalLang, FictionalTool' in result.text
    assert 'Fictional Corp, Fictional Scientist, 2015-2020' in result.text
    assert 'PhD in Fictional Science, Fictional University' in result.text
    assert 'Fictional open-source fictional-parser' in result.text


def test_colon_merged_headings_split_with_high_confidence():
    text = (
        'Summary of Skills: FictionalLang, FictionalTool, FictionalFramework\n'
        'Professional Experience: Fictional Corp, Fictional Scientist, 2018-2024\n'
    )
    result = repair_section_headings(text)
    lines = result.text.splitlines()
    assert lines[0] == SKILLS
    assert lines[1] == 'FictionalLang, FictionalTool, FictionalFramework'
    assert lines[2] == EXPERIENCE
    assert lines[3] == 'Fictional Corp, Fictional Scientist, 2018-2024'
    assert result.report.mapped_headings == [SKILLS, EXPERIENCE]


def test_no_space_merged_headings_split_with_high_confidence():
    text = (
        'EducationPhD in Fictional Chemistry, Fictional University\n'
        'ProjectsFictional-simulation-toolkit\n'
    )
    result = repair_section_headings(text)
    lines = result.text.splitlines()
    assert lines[0] == EDUCATION
    assert lines[1] == 'PhD in Fictional Chemistry, Fictional University'
    assert lines[2] == PROJECTS
    assert lines[3] == 'Fictional-simulation-toolkit'
    assert result.report.mapped_headings == [EDUCATION, PROJECTS]


def test_allcaps_space_merged_heading_splits_with_high_confidence():
    text = 'EMPLOYMENT HISTORY Fictional Corp, Senior Fictional Scientist, 2016-2021\n'
    result = repair_section_headings(text)
    lines = result.text.splitlines()
    assert lines[0] == EXPERIENCE
    assert lines[1] == 'Fictional Corp, Senior Fictional Scientist, 2016-2021'
    assert result.report.mapped_headings == [EXPERIENCE]


def test_technical_and_scientific_skills_variants_map_to_skills():
    for heading in ('Technical & Scientific Skills', 'Technical and Scientific Skills'):
        result = repair_section_headings(f'{heading}:\nFictionalChemInformatics, FictionalML\n')
        assert result.text.splitlines()[0] == SKILLS
        assert result.report.mapped_headings == [SKILLS]


def test_selected_ai_data_science_projects_heading_maps_to_projects():
    text = 'Selected AI, Data Science & Application Projects: Fictional recommender system\n'
    result = repair_section_headings(text)
    lines = result.text.splitlines()
    assert lines[0] == PROJECTS
    assert lines[1] == 'Fictional recommender system'
    assert result.report.mapped_headings == [PROJECTS]


def test_publications_and_patents_maps_to_its_own_section():
    # Phase 7G.5G: publicly available publication/patent citations (including
    # coauthor and candidate names) are preserved locally, so this heading now
    # maps to a recognized section rather than being left unmapped.
    text = 'Publications and PatentsFictional Patent App. No. ABC-123, Fictional Compound Z\n'
    result = repair_section_headings(text)
    lines = result.text.splitlines()
    assert lines[0] == PUBLICATIONS
    assert lines[1] == 'Fictional Patent App. No. ABC-123, Fictional Compound Z'
    assert result.report.mapped_headings == [PUBLICATIONS]
    assert result.report.unmapped_headings == []
    assert result.report.needs_manual_review is False


def test_ambiguous_sentence_starting_with_heading_word_is_left_untouched():
    text = 'Skills development was central to my role as a fictional research scientist.\n'
    result = repair_section_headings(text)
    assert result.text == text.rstrip('\n')
    assert result.report.ambiguous_count == 1
    assert result.report.mapped_headings == []
    assert result.report.needs_manual_review is True


def test_word_that_merely_starts_with_a_heading_phrase_is_not_split():
    # "Skillset" is not "Skills" + content; the lowercase continuation with no
    # separating whitespace must block the match entirely.
    text = 'Skillset Fictional summary line about soft skills.\n'
    result = repair_section_headings(text)
    assert result.text == text.rstrip('\n')
    assert result.report.ambiguous_count == 0
    assert result.report.mapped_headings == []
    assert result.report.unmapped_headings == []


def test_unrelated_content_is_never_modified():
    text = 'Fictional summary line unrelated to any heading.\nAnother plain content line.\n'
    result = repair_section_headings(text)
    assert result.text == text.rstrip('\n')
    assert result.report.mapped_headings == []
    assert result.report.unmapped_headings == []
    assert result.report.ambiguous_count == 0


def test_blank_lines_preserved_unchanged():
    text = 'Education\nFictional degree\n\nProjects\nFictional project\n'
    result = repair_section_headings(text)
    assert '\n\n' in result.text


# --- Fictional, full-layout regression tests for the three resume variants ---

_PHARMA_LAYOUT = (
    'FICTIONAL_CANDIDATE_HEADER\n'
    'Professional Summary: Fictional medicinal chemist with fictional PROTAC experience.\n'
    'Technical Skills: FictionalSAR, FictionalPROTAC, FictionalHPLC\n'
    'Employment HistoryFictional Pharma Inc, Senior Fictional Scientist, eight fictional years\n'
    'Education\n'
    'PhD in Fictional Organic Chemistry, Fictional University\n'
    'Publications and PatentsFictional Coauthor A, Fictional Candidate, Fictional Journal of '
    'Fictional Oncology, Fictional Patent App. No. ABC-123\n'
)

_DATA_LAYOUT = (
    'FICTIONAL_CANDIDATE_HEADER\n'
    'Summary of Skills: FictionalPython, FictionalSQL, FictionalSpark\n'
    'EMPLOYMENT HISTORY Fictional Analytics Co, Fictional Data Engineer, five fictional years\n'
    'Projects\n'
    'Fictional ETL pipeline for fictional telemetry data\n'
    'Education\n'
    'BSc in Fictional Computer Science, Fictional University\n'
)

_SCIENTIFIC_AI_LAYOUT = (
    'FICTIONAL_CANDIDATE_HEADER\n'
    'Technical & Scientific Skills: FictionalRDKit, FictionalPyTorch, FictionalCheminformatics\n'
    'Selected AI, Data Science & Application Projects: Fictional molecule-generation model\n'
    'Professional Experience: Fictional BioAI Labs, Fictional Research Scientist, four fictional years\n'
    'Education\n'
    'PhD in Fictional Computational Chemistry, Fictional University\n'
)


def _assert_recognized_sections_survive_preview(repaired_text, expected_fragments):
    preview = preview_resume(repaired_text, identifiers=[])
    for fragment in expected_fragments:
        assert fragment in preview
    # The merged candidate header line is never a recognized section and must
    # still be excluded, proving sanitization was not weakened.
    assert 'FICTIONAL_CANDIDATE_HEADER' not in preview


def test_pharma_layout_recovers_skills_experience_education_and_publications():
    result = repair_section_headings(_PHARMA_LAYOUT)
    _assert_recognized_sections_survive_preview(result.text, [
        'FictionalSAR, FictionalPROTAC, FictionalHPLC',
        'Fictional Pharma Inc, Senior Fictional Scientist, eight fictional years',
        'PhD in Fictional Organic Chemistry, Fictional University',
    ])
    # Publications and Patents is now a recognized section (Phase 7G.5G): the
    # coauthor/candidate citation content is preserved in the local preview.
    preview = preview_resume(result.text, identifiers=['Fictional Candidate'])
    assert 'Fictional Coauthor A, Fictional Candidate' in preview
    assert 'Fictional Patent App. No. ABC-123' in preview
    assert result.report.unmapped_headings == []
    assert result.report.mapped_headings[-1] == PUBLICATIONS


def test_data_layout_recovers_skills_experience_projects_and_education():
    result = repair_section_headings(_DATA_LAYOUT)
    _assert_recognized_sections_survive_preview(result.text, [
        'FictionalPython, FictionalSQL, FictionalSpark',
        'Fictional Analytics Co, Fictional Data Engineer, five fictional years',
        'Fictional ETL pipeline for fictional telemetry data',
        'BSc in Fictional Computer Science, Fictional University',
    ])
    assert result.report.ambiguous_count == 0
    assert result.report.unmapped_headings == []


def test_scientific_ai_layout_recovers_skills_projects_experience_and_education():
    result = repair_section_headings(_SCIENTIFIC_AI_LAYOUT)
    _assert_recognized_sections_survive_preview(result.text, [
        'FictionalRDKit, FictionalPyTorch, FictionalCheminformatics',
        'Fictional molecule-generation model',
        'Fictional BioAI Labs, Fictional Research Scientist, four fictional years',
        'PhD in Fictional Computational Chemistry, Fictional University',
    ])
    assert result.report.ambiguous_count == 0
    assert result.report.unmapped_headings == []


def test_repair_never_bypasses_strict_approval_requirement():
    result = repair_section_headings(_DATA_LAYOUT)
    preview = preview_resume(result.text, identifiers=[])
    with pytest.raises(ResumePrivacyError):
        approve_resume(preview, confirmed=False)
    approved = approve_resume(preview, confirmed=True)
    assert str(approved) == preview
