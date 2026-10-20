# JobPilot-AI

**AI-Powered Job Discovery, Matching, and Resume Analysis Platform**

JobPilot-AI is a full-stack application built with Python, FastAPI, React, and AI-assisted workflows to streamline job discovery, evaluate career opportunities, and help candidates make informed application decisions.

The project combines automated job collection, structured job analysis, candidate-to-job matching, resume recommendations, and an interactive analytics dashboard.

## Project Overview

Finding relevant job opportunities across multiple platforms can be time-consuming. JobPilot-AI aims to simplify this process by bringing job discovery, analysis, and application preparation into a single workflow.

The application is designed to:

- Collect job opportunities from supported applicant tracking systems.
- Organize job postings into a searchable interface.
- Analyze job descriptions and identify relevant requirements.
- Compare job requirements against candidate qualifications.
- Support resume selection and tailored application preparation.
- Provide AI-assisted insights to support job-search decisions.

## Key Features

### 1. Automated Job Discovery

- Python-based job collection from Greenhouse and Lever.
- Structured extraction and processing of job information.
- Role-based and location-based filtering.
- Job description retrieval and enrichment.

### 2. Job Matching and Analysis

- Candidate-to-job matching workflows.
- Structured analysis of job descriptions.
- Identification of required qualifications and skills.
- Job classification and relevance assessment.
- Comparison of job requirements against candidate evidence.

### 3. AI-Assisted Career Insights

- OpenAI integration for supported analysis workflows.
- Structured AI responses for consistent downstream processing.
- AI-assisted interpretation of job requirements.
- Personalized analysis based on candidate qualifications.
- Agent-oriented workflow components for research, resume analysis, and response evaluation.

### 4. Resume Analysis and Recommendations

- Resume text processing and analysis.
- Resume selection support.
- Requirement-by-requirement qualification comparisons.
- Evidence-based recommendations for application preparation.
- Privacy controls for handling candidate information.

### 5. Interactive Dashboard

The React frontend provides dedicated interfaces for:

- Dashboard overview and job statistics.
- Job discovery and filtering.
- Job listings and detailed job descriptions.
- Job matching and requirement comparisons.
- AI insights.
- Resume recommendations.

## Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, JavaScript, Vite |
| Database | SQLAlchemy, Alembic |
| AI Integration | OpenAI API, structured outputs |
| Data Processing | Python, REST APIs, JSON |
| Job Sources | Greenhouse API, Lever API |
| Testing | pytest, Vitest, React Testing Library |
| Development Tools | Git, GitHub, VS Code |

## Application Architecture

```text
                  JobPilot-AI
                       |
          +------------+------------+
          |                         |
     React Frontend            FastAPI Backend
          |                         |
     Dashboard UI              REST Endpoints
     Job Discovery                  |
     Job Matches         +----------+----------+
     AI Insights         |          |          |
     Resume Tools    Job Sources  Matching   AI Workflows
                         |          |          |
                    Greenhouse   Candidate   OpenAI API
                       Lever     Evidence    Integration
                                    |
                              Data Persistence
```

The frontend communicates with the FastAPI backend through REST endpoints. The backend coordinates job collection, data access, matching logic, and AI-assisted analysis.

## Project Structure

```text
jobpilot-ai/
├── frontend/             # React frontend
├── src/
│   ├── ai/               # AI clients, agents, and analysis
│   ├── api.py            # FastAPI endpoints
│   ├── greenhouse.py     # Greenhouse job collection
│   ├── lever.py          # Lever job collection
│   ├── matching.py       # Job matching logic
│   ├── models.py         # Database models
│   └── repository.py     # Data access
├── alembic/              # Database migrations
├── scripts/              # Supporting automation scripts
├── tests/                # Backend tests
├── docs/                 # Technical documentation
├── requirements.txt      # Python dependencies
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12
- Node.js and npm
- Git
- A configured database for workflows requiring persistence
- OpenAI API credentials for live AI-powered features

### Clone the Repository

```bash
git clone https://github.com/Vdevannah/jobpilot-ai.git
cd jobpilot-ai
```

### Backend Setup

Create a Python virtual environment and install the project dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Database configuration and any required environment variables must be completed before running features that depend on external services or persistence.

### Frontend Setup

```bash
cd frontend
npm install
```

For additional frontend setup information, see `frontend/README.md` and `docs/DASHBOARD_DEV_SETUP.md`.

## Testing

The project includes automated tests for backend APIs, job discovery, matching, AI workflows, resume processing, and frontend components.

**Latest verified Python test result: 746 tests passed.**

Run the Python test suite:

```bash
python -m pytest -q
```

Run the frontend tests from the `frontend` directory:

```bash
npm test
```

*The Python test result reflects the latest local verification. Frontend test results are not included in that count.*

## Development Status

JobPilot-AI is under active development.

The repository includes implemented job discovery, matching, AI analysis, resume-processing, and dashboard components. Some workflows support mock or fixture-based execution for development and automated testing.

Live job retrieval, AI analysis, and database-dependent functionality require the corresponding external services, credentials, and runtime configuration. The presence of an integration does not imply that every workflow is deployed or continuously running.

## Planned Enhancements

- Expand live job-source coverage.
- Improve job matching and recommendation quality.
- Strengthen end-to-end integration of job discovery and AI analysis.
- Improve deployment and cloud infrastructure.
- Enhance the application-assistance workflow.
- Add further operational monitoring and reliability improvements.

## Author

**Vijayarajan Devannah, Ph.D.**

Organic Chemistry Research Scientist | Python Developer | Data Engineering & Analytics | AI-Assisted Application Development

[GitHub Profile](https://github.com/Vdevannah)

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
