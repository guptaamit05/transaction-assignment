import threading
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Customer, Transaction, WorkerJob
from app.worker import process_transaction


def create_customer():
    db = SessionLocal()

    try:
        customer = Customer(
            customer_id="CONCURRENT-CUST",
            name="Concurrency Test",
            balance=Decimal("1000.00"),
        )

        db.add(customer)
        db.commit()

    finally:
        db.close()


def create_transaction(transaction_id):
    db = SessionLocal()

    try:
        transaction = Transaction(
            transaction_id=transaction_id,
            customer_id="CONCURRENT-CUST",
            transaction_type="DEBIT",
            amount=Decimal("700.00"),
            status="PROCESSING",
            attempts=1,
        )

        job = WorkerJob(
            transaction_id=transaction_id,
            status="PROCESSING",
            attempts=1,
            max_attempts=3,
        )

        db.add(transaction)
        db.add(job)

        db.commit()

    finally:
        db.close()


def test_concurrent_debits():
    create_customer()

    create_transaction("CONCURRENT-TXN-1")
    create_transaction("CONCURRENT-TXN-2")

    threads = [
        threading.Thread(
            target=process_transaction,
            args=("CONCURRENT-TXN-1",),
        ),
        threading.Thread(
            target=process_transaction,
            args=("CONCURRENT-TXN-2",),
        ),
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    db = SessionLocal()

    try:
        customer = (
            db.execute(
                select(Customer)
                .where(
                    Customer.customer_id == "CONCURRENT-CUST"
                )
            )
            .scalars()
            .one()
        )

        transactions = (
            db.execute(
                select(Transaction)
                .where(
                    Transaction.customer_id == "CONCURRENT-CUST"
                )
            )
            .scalars()
            .all()
        )

        successful = [
            tx for tx in transactions
            if tx.status == "SUCCESS"
        ]

        failed = [
            tx for tx in transactions
            if tx.status == "FAILED"
        ]

        assert len(successful) == 1
        assert len(failed) == 1
        assert customer.balance == Decimal("300.00")

    finally:
        db.close()