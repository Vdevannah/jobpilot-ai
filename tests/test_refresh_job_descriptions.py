from unittest.mock import MagicMock, patch

import requests

from src.models import Job
from scripts.refresh_job_descriptions import (
    default_board_token,
    extract_greenhouse_job_id,
    find_refreshable_jobs,
    is_demo_record,
    main,
    summarize_change,
)


def test_default_board_token_slugifies_company_name():
    assert default_board_token("Airbnb") == "airbnb"
    assert default_board_token("Acme Corp!") == "acmecorp"


def test_extract_greenhouse_job_id_reads_gh_jid_query_param():
    assert extract_greenhouse_job_id("https://careers.airbnb.com/positions/8031901?gh_jid=8031901") == "8031901"


def test_extract_greenhouse_job_id_returns_none_when_absent():
    assert extract_greenhouse_job_id("https://careers.airbnb.com/positions/8031901") is None
    assert extract_greenhouse_job_id("https://example.com/jobs/1") is None


def test_is_demo_record_detects_the_placeholder_domain_only():
    assert is_demo_record("https://example.com/jobs/1") is True
    assert is_demo_record("https://www.example.com/jobs/1") is True
    assert is_demo_record("https://careers.airbnb.com/positions/1") is False


def test_summarize_change_reports_unchanged_when_identical():
    job = Job(description="Same text.")
    assert summarize_change(job, "Same text.") == "unchanged"


def test_summarize_change_reports_structure_gain():
    job = Job(description="Flat text with no structure at all.")
    result = summarize_change(job, "Paragraph one.\n\nParagraph two.")
    assert "paragraph/list structure" in result
    assert "chars ->" in result


def _make_job(id_, company, url, description="old flat description"):
    job = Job(
        id=id_, title="Some Role", company=company, location="Remote",
        url=url, source="greenhouse", description=description,
    )
    return job


def test_find_refreshable_jobs_excludes_demo_records_and_jobs_without_gh_jid():
    session = MagicMock()
    jobs = [
        _make_job(1, "Acme", "https://example.com/jobs/1"),  # demo -- excluded
        _make_job(2, "Airbnb", "https://careers.airbnb.com/positions/2"),  # no gh_jid -- excluded
        _make_job(3, "Airbnb", "https://careers.airbnb.com/positions/3?gh_jid=3"),  # eligible
    ]
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = jobs

    result = find_refreshable_jobs(session)

    assert [job.id for job, _gh_jid in result] == [3]
    assert result[0][1] == "3"


def test_find_refreshable_jobs_can_filter_to_an_explicit_id_allowlist():
    session = MagicMock()
    job = _make_job(7, "Airbnb", "https://careers.airbnb.com/positions/7?gh_jid=7")
    session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [job]

    find_refreshable_jobs(session, job_ids=[4, 7])

    # filter() called twice: once for source == "greenhouse", once for id IN (...).
    assert session.query.return_value.filter.return_value.filter.called


def test_dry_run_never_writes_to_the_database(capsys):
    job = _make_job(4, "Airbnb", "https://careers.airbnb.com/positions/4?gh_jid=4", description="old")
    session = MagicMock()
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [job]

    fake_response = MagicMock()
    fake_response.json.return_value = {"content": "<p>New paragraph one.</p><p>New paragraph two.</p>"}

    with patch("scripts.refresh_job_descriptions.SessionLocal", return_value=session), \
         patch("scripts.refresh_job_descriptions.requests.get", return_value=fake_response), \
         patch("sys.argv", ["refresh_job_descriptions.py"]):
        main()

    assert job.description == "old"  # untouched
    session.commit.assert_not_called()
    output = capsys.readouterr().out
    assert "DRY RUN" in output
    assert "no database changes were made" in output


def test_apply_mode_updates_only_the_description_field_and_commits(capsys):
    job = _make_job(4, "Airbnb", "https://careers.airbnb.com/positions/4?gh_jid=4", description="old")
    original_title, original_company, original_url = job.title, job.company, job.url
    session = MagicMock()
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [job]

    fake_response = MagicMock()
    fake_response.json.return_value = {"content": "<p>New paragraph one.</p><p>New paragraph two.</p>"}

    with patch("scripts.refresh_job_descriptions.SessionLocal", return_value=session), \
         patch("scripts.refresh_job_descriptions.requests.get", return_value=fake_response), \
         patch("sys.argv", ["refresh_job_descriptions.py", "--apply"]):
        main()

    assert job.description == "New paragraph one.\n\nNew paragraph two."
    assert job.title == original_title
    assert job.company == original_company
    assert job.url == original_url
    session.commit.assert_called_once()
    session.add.assert_not_called()  # update only, never an insert
    output = capsys.readouterr().out
    assert "APPLY MODE" in output


def test_a_404_for_one_job_does_not_stop_or_crash_the_others(capsys):
    jobs = [
        _make_job(5, "Airbnb", "https://careers.airbnb.com/positions/5?gh_jid=5", description="old5"),
        _make_job(6, "Airbnb", "https://careers.airbnb.com/positions/6?gh_jid=6", description="old6"),
    ]
    session = MagicMock()
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = jobs

    ok_response = MagicMock()
    ok_response.json.return_value = {"content": "<p>Fresh content.</p>"}

    def fake_get(url, timeout=None):
        if "gh_jid" in url or "/5" in url:
            pass
        if url.endswith("/5"):
            raise requests.RequestException("404 Client Error")
        return ok_response

    with patch("scripts.refresh_job_descriptions.SessionLocal", return_value=session), \
         patch("scripts.refresh_job_descriptions.requests.get", side_effect=fake_get), \
         patch("sys.argv", ["refresh_job_descriptions.py"]):
        main()

    assert jobs[0].description == "old5"  # the 404'd job is untouched
    output = capsys.readouterr().out
    assert "SKIPPED" in output


def test_refuses_to_overwrite_with_an_empty_live_result(capsys):
    job = _make_job(4, "Airbnb", "https://careers.airbnb.com/positions/4?gh_jid=4", description="old")
    session = MagicMock()
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [job]

    empty_response = MagicMock()
    empty_response.json.return_value = {"content": ""}

    with patch("scripts.refresh_job_descriptions.SessionLocal", return_value=session), \
         patch("scripts.refresh_job_descriptions.requests.get", return_value=empty_response), \
         patch("sys.argv", ["refresh_job_descriptions.py", "--apply"]):
        main()

    assert job.description == "old"
    assert "SKIPPED" in capsys.readouterr().out


def test_reports_when_no_refreshable_jobs_exist(capsys):
    session = MagicMock()
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    with patch("scripts.refresh_job_descriptions.SessionLocal", return_value=session), \
         patch("sys.argv", ["refresh_job_descriptions.py"]):
        main()

    assert "No refreshable jobs found" in capsys.readouterr().out


def test_refuses_to_proceed_when_the_allowlist_does_not_exactly_match_eligible_jobs(capsys):
    # Requested ids 4 and 9, but only 4 is actually eligible (9 is, say, a
    # demo record or missing a gh_jid) -- the mismatch must block the run
    # entirely, not silently proceed with whatever subset was found.
    job4 = _make_job(4, "Airbnb", "https://careers.airbnb.com/positions/4?gh_jid=4", description="old4")
    session = MagicMock()
    session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [job4]

    with patch("scripts.refresh_job_descriptions.SessionLocal", return_value=session), \
         patch("sys.argv", ["refresh_job_descriptions.py", "--job-id", "4", "--job-id", "9", "--apply"]):
        main()

    assert job4.description == "old4"
    session.commit.assert_not_called()
    output = capsys.readouterr().out
    assert "REFUSING TO PROCEED" in output
    assert "[9]" in output or "9" in output


def test_explicit_allowlist_of_several_ids_updates_only_those(capsys):
    jobs = [
        _make_job(4, "Airbnb", "https://careers.airbnb.com/positions/4?gh_jid=4", description="old4"),
        _make_job(6, "Airbnb", "https://careers.airbnb.com/positions/6?gh_jid=6", description="old6"),
    ]
    session = MagicMock()
    session.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = jobs

    ok_response = MagicMock()
    ok_response.json.return_value = {"content": "<p>Fresh content.</p>"}

    with patch("scripts.refresh_job_descriptions.SessionLocal", return_value=session), \
         patch("scripts.refresh_job_descriptions.requests.get", return_value=ok_response), \
         patch("sys.argv", ["refresh_job_descriptions.py", "--job-id", "4", "--job-id", "6", "--apply"]):
        main()

    assert jobs[0].description == "Fresh content."
    assert jobs[1].description == "Fresh content."
    session.commit.assert_called_once()
