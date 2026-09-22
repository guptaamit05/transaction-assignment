import os
import socket
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Customer, Transaction, WorkerJob


STALE_JOB_TIMEOUT_SECONDS = 60


WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


def claim_job(db: Session):
    """
    Claim one pending job safely.
    Multiple workers can call this because of SKIP LOCKED.
    """

    job = (
        db.execute(
            select(WorkerJob)
            .where(
                WorkerJob.status == "PENDING",
                WorkerJob.available_at <= datetime.now(timezone.utc),
            )
            .order_by(WorkerJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        .scalars()
        .first()
    )

    if not job:
        return None

    job.status = "PROCESSING"
    job.attempts += 1
    job.locked_at = datetime.now(timezone.utc)
    job.locked_by = WORKER_ID
    job.last_error = None

    transaction = (
        db.execute(
            select(Transaction)
            .where(Transaction.transaction_id == job.transaction_id)
            .with_for_update()
        )
        .scalars()
        .one()
    )

    transaction.status = "PROCESSING"
    transaction.attempts = job.attempts
    transaction.processing_started_at = datetime.now(timezone.utc)
    transaction.last_attempt_at = datetime.now(timezone.utc)

    db.commit()

    return job.transaction_id


def process_transaction(transaction_id: str):
    """
    Process one transaction atomically.
    """

    db = SessionLocal()

    try:
        transaction = (
            db.execute(
                select(Transaction)
                .where(Transaction.transaction_id == transaction_id)
                .with_for_update()
            )
            .scalars()
            .one()
        )

        job = (
            db.execute(
                select(WorkerJob)
                .where(WorkerJob.transaction_id == transaction_id)
                .with_for_update()
            )
            .scalars()
            .one()
        )

        # Important: don't apply a transaction twice.
        if transaction.status == "SUCCESS":
            job.status = "SUCCESS"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        customer = (
            db.execute(
                select(Customer)
                .where(Customer.customer_id == transaction.customer_id)
                .with_for_update()
            )
            .scalars()
            .one()
        )

        # Business rule: debit cannot make balance negative.
        if (
            transaction.transaction_type == "DEBIT"
            and customer.balance < transaction.amount
        ):
            transaction.status = "FAILED"
            transaction.failure_reason = "Insufficient balance"

            job.status = "FAILED"
            job.last_error = "Insufficient balance"
            job.completed_at = datetime.now(timezone.utc)

            db.commit()
            return

        # Apply transaction.
        if transaction.transaction_type == "CREDIT":
            customer.balance += transaction.amount
        else:
            customer.balance -= transaction.amount

        # Mark everything successful in the SAME DB transaction.
        transaction.status = "SUCCESS"
        transaction.completed_at = datetime.now(timezone.utc)
        transaction.failure_reason = None

        job.status = "SUCCESS"
        job.completed_at = datetime.now(timezone.utc)
        job.last_error = None

        db.commit()

    except Exception as exc:
        db.rollback()

        try:
            transaction = (
                db.execute(
                    select(Transaction)
                    .where(Transaction.transaction_id == transaction_id)
                    .with_for_update()
                )
                .scalars()
                .one()
            )

            job = (
                db.execute(
                    select(WorkerJob)
                    .where(WorkerJob.transaction_id == transaction_id)
                    .with_for_update()
                )
                .scalars()
                .one()
            )

            retry_or_fail(
                db,
                transaction,
                job,
                str(exc),
            )

        except Exception as retry_error:
            db.rollback()
            print(
                f"Could not update retry state for "
                f"{transaction_id}: {retry_error}"
            )

    finally:
        db.close()


def recover_stale_jobs():
    db = SessionLocal()

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=STALE_JOB_TIMEOUT_SECONDS
        )

        jobs = (
            db.execute(
                select(WorkerJob)
                .where(
                    WorkerJob.status == "PROCESSING",
                    WorkerJob.locked_at < cutoff,
                )
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )

        for job in jobs:
            transaction = (
                db.execute(
                    select(Transaction)
                    .where(
                        Transaction.transaction_id == job.transaction_id
                    )
                    .with_for_update()
                )
                .scalars()
                .one()
            )

            # Very important:
            # If financial processing already succeeded,
            # NEVER put the transaction back into PENDING.
            if transaction.status == "SUCCESS":
                job.status = "SUCCESS"
                job.locked_at = None
                job.locked_by = None
                job.completed_at = datetime.now(timezone.utc)

                continue

            # If it was processing but never completed,
            # make it available to another worker.
            job.status = "PENDING"
            job.available_at = datetime.now(timezone.utc)

            job.locked_at = None
            job.locked_by = None

            transaction.status = "PENDING"

            print(
                f"Recovered stale job: {job.transaction_id}"
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
        

def worker_loop():
    print(f"Worker started: {WORKER_ID}")

    while True:
        
        # Recover jobs abandoned by crashed workers.
        recover_stale_jobs()
        
        db = SessionLocal()

        try:
            transaction_id = claim_job(db)
        finally:
            db.close()

        if transaction_id:
            print(f"Processing transaction: {transaction_id}")
            process_transaction(transaction_id)
        else:
            # No job currently available.
            import time
            time.sleep(1)



def retry_or_fail(db: Session, transaction: Transaction, job: WorkerJob, error: str):
    """
    Retry transient failures with exponential backoff.
    Permanently fail after max_attempts.
    """

    now = datetime.now(timezone.utc)

    transaction.failure_reason = error
    job.last_error = error

    if job.attempts < job.max_attempts:
        delay_seconds = 2 ** job.attempts

        job.status = "PENDING"
        job.available_at = now + timedelta(seconds=delay_seconds)
        job.locked_at = None
        job.locked_by = None

        transaction.status = "PENDING"

        print(
            f"Retrying {transaction.transaction_id} "
            f"in {delay_seconds} seconds "
            f"(attempt {job.attempts}/{job.max_attempts})"
        )

    else:
        job.status = "FAILED"
        job.locked_at = None
        job.locked_by = None
        job.completed_at = now

        transaction.status = "FAILED"

        print(
            f"Transaction {transaction.transaction_id} "
            f"failed permanently after {job.attempts} attempts"
        )

    db.commit()


if __name__ == "__main__":
    worker_loop()