from sqlalchemy import select

from src.database import SessionLocal
from src.models import Job


def save_jobs(jobs):
    session = SessionLocal()
    added_count = 0

    try:
        for job_data in jobs:
            existing_job = session.scalar(
                select(Job).where(
                    Job.company == job_data["company"],
                    Job.title == job_data["title"],
                    Job.location == job_data["location"],
                )
            )

            if existing_job is not None:
                continue

            job = Job(
                title=job_data["title"],
                company=job_data["company"],
                location=job_data["location"],
                url=job_data["url"],
                source=job_data["source"],
            )
            session.add(job)
            added_count += 1

        session.commit()
        return added_count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_all_jobs():
    session = SessionLocal()

    try:
        return session.scalars(select(Job)).all()
    finally:
        session.close()


def get_job_by_id(job_id):
    session = SessionLocal()

    try:
        return session.get(Job, job_id)
    finally:
        session.close()
