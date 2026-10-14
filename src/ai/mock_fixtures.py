"""Fictional structured resume evidence shared by local mock workflows."""

from src.ai.schemas import ResumeAnalysis


FICTIONAL_RESUME_VARIANTS: dict[str, ResumeAnalysis] = {
    'pharma': ResumeAnalysis(
        skills=['SAR', 'PROTACs', 'medicinal chemistry'],
        professional_experience_years={'pharma': 8.0},
        domains=['pharma'],
        education=['PhD in Organic Chemistry (fictional)'],
        summary='Fictional pharma resume variant for demonstration only.',
    ),
    'data': ResumeAnalysis(
        skills=['Python', 'SQL', 'data engineering'],
        professional_experience_years={'data': 3.0},
        domains=['data'],
        education=['BSc in Computer Science (fictional)'],
        summary='Fictional data resume variant for demonstration only.',
    ),
    'scientific_ai': ResumeAnalysis(
        skills=['Python', 'cheminformatics', 'RDKit', 'machine learning'],
        professional_experience_years={},
        domains=[],
        education=['PhD in Computational Chemistry (fictional)'],
        summary='Fictional scientific_ai resume variant for demonstration only.',
    ),
}