from fastapi import Depends, FastAPI, HTTPException, status, Query
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Transaction, WorkerJob
from app.schemas import TransactionCreate, TransactionResponse, TransactionListResponse
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Transaction Processing System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "healthy",
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "unhealthy",
            "error": str(e),
        }


@app.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # 1. Check customer exists
    # ---------------------------------------------------------

    customer = (
        db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # ---------------------------------------------------------
    # 2. Idempotency check
    # ---------------------------------------------------------

    existing_transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == payload.transaction_id)
        .first()
    )

    if existing_transaction:
        same_transaction = (
            existing_transaction.customer_id == payload.customer_id
            and existing_transaction.transaction_type == payload.transaction_type
            and existing_transaction.amount == payload.amount
        )

        if not same_transaction:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Transaction ID already exists with different transaction data"),
            )

        return existing_transaction

    # ---------------------------------------------------------
    # 3. Create transaction
    # ---------------------------------------------------------

    transaction = Transaction(
        transaction_id=payload.transaction_id,
        customer_id=payload.customer_id,
        transaction_type=payload.transaction_type,
        amount=payload.amount,
        status="PENDING",
        attempts=0,
    )

    db.add(transaction)

    # ---------------------------------------------------------
    # 4. Create persistent worker job
    # ---------------------------------------------------------

    worker_job = WorkerJob(
        transaction_id=payload.transaction_id,
        status="PENDING",
        attempts=0,
        max_attempts=3,
    )

    db.add(worker_job)

    # ---------------------------------------------------------
    # 5. Atomic commit
    # ---------------------------------------------------------

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        # Another request may have created the same
        # transaction concurrently.
        existing_transaction = (
            db.query(Transaction)
            .filter(Transaction.transaction_id == payload.transaction_id)
            .first()
        )

        if existing_transaction:
            return existing_transaction

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction could not be created",
        )

    # Refresh from database
    db.refresh(transaction)

    return transaction


@app.post(
    "/transactions/{transaction_id}/retry",
    response_model=TransactionResponse,
)
def retry_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .with_for_update()
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    if transaction.status != "FAILED":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Transaction cannot be retried "
                f"from status {transaction.status}"
            ),
        )

    job = (
        db.query(WorkerJob)
        .filter(
            WorkerJob.transaction_id == transaction_id
        )
        .with_for_update()
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=500,
            detail="Worker job not found",
        )

    # Reset the job for manual retry.
    job.status = "PENDING"
    job.available_at = datetime.now(timezone.utc)

    job.locked_at = None
    job.locked_by = None
    job.last_error = None
    job.completed_at = None

    transaction.status = "PENDING"
    transaction.failure_reason = None

    db.commit()
    db.refresh(transaction)

    return transaction



@app.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return transaction

@app.get("/customers/{customer_id}/balance")
def get_customer_balance(
    customer_id: str,
    db: Session = Depends(get_db),
):
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return {
        "customer_id": customer.customer_id,
        "balance": customer.balance,
    }
    

@app.get(
    "/customers/{customer_id}/transactions",
    response_model=TransactionListResponse,
)
def get_customer_transactions(
    customer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    transaction_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    query = db.query(Transaction).filter(
        Transaction.customer_id == customer_id
    )

    if transaction_type:
        transaction_type = transaction_type.upper()

        if transaction_type not in {"CREDIT", "DEBIT"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid transaction type",
            )

        query = query.filter(
            Transaction.transaction_type == transaction_type
        )

    if status:
        status = status.upper()

        if status not in {
            "PENDING",
            "PROCESSING",
            "SUCCESS",
            "FAILED",
        }:
            raise HTTPException(
                status_code=400,
                detail="Invalid transaction status",
            )

        query = query.filter(
            Transaction.status == status
        )

    total = query.count()

    transactions = (
        query
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": transactions,
        "page": page,
        "page_size": page_size,
        "total": total,
    }
    
@app.get(
    "/transactions",
    response_model=TransactionListResponse,
)
def get_all_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    transaction_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Transaction)

    # Filter by transaction type
    if transaction_type:
        transaction_type = transaction_type.upper()

        if transaction_type not in {"CREDIT", "DEBIT"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid transaction type",
            )

        query = query.filter(
            Transaction.transaction_type == transaction_type
        )

    # Filter by status
    if status:
        status = status.upper()

        if status not in {
            "PENDING",
            "PROCESSING",
            "SUCCESS",
            "FAILED",
        }:
            raise HTTPException(
                status_code=400,
                detail="Invalid transaction status",
            )

        query = query.filter(
            Transaction.status == status
        )

    total = query.count()

    transactions = (
        query
        .order_by(Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": transactions,
        "page": page,
        "page_size": page_size,
        "total": total,
    }