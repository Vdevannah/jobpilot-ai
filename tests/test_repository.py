from unittest.mock import MagicMock, patch

from src.models import Job
from src.repository import get_all_jobs, get_job_by_id, save_jobs


def test_save_jobs_adds_new_job():
    session = MagicMock()
    session.scalar.return_value = None

    with patch("src.repository.SessionLocal", return_value=session):
        result = save_jobs([
            {
                "title": "Data Engineer",
                "company": "Acme",
                "location": "New York, NY",
                "url": "https://example.com/1",
                "source": "greenhouse",
            }
        ])

    added_job = session.add.call_args[0][0]
    assert isinstance(added_job, Job)
    assert added_job.title == "Data Engineer"
    assert added_job.company == "Acme"
    assert added_job.location == "New York, NY"
    assert added_job.url == "https://example.com/1"
    assert added_job.source == "greenhouse"
    session.commit.assert_called_once()
    assert result == 1
    session.close.assert_called_once()


def test_save_jobs_skips_existing_job():
    session = MagicMock()
    session.scalar.return_value = Job()

    with patch("src.repository.SessionLocal", return_value=session):
        result = save_jobs([
            {
                "title": "Data Engineer",
                "company": "Acme",
                "location": "New York, NY",
                "url": "https://example.com/1",
                "source": "greenhouse",
            }
        ])

    session.add.assert_not_called()
    session.commit.assert_called_once()
    assert result == 0
    session.close.assert_called_once()


def test_get_all_jobs_returns_jobs():
    session = MagicMock()
    expected_jobs = [Job(), Job()]
    session.scalars.return_value.all.return_value = expected_jobs

    with patch("src.repository.SessionLocal", return_value=session):
        result = get_all_jobs()

    assert result == expected_jobs
    session.close.assert_called_once()


def test_get_job_by_id_returns_job():
    session = MagicMock()
    expected_job = Job()
    session.get.return_value = expected_job

    with patch("src.repository.SessionLocal", return_value=session):
        result = get_job_by_id(123)

    session.get.assert_called_once_with(Job, 123)
    assert result is expected_job
    session.close.assert_called_once()
