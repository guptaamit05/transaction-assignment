### 1. Add `backend/.env`

Copy db url:

`backend/.env.example`

```text
database_url=postgresql+psycopg2://transaction_user:transaction_pass@localhost:5432/transaction_db
````

to 

```text
backend/.env
```

and change the credentials if necessary.

---

# Transaction Processing System

A production-oriented full-stack transaction processing system built with **FastAPI, PostgreSQL, React, and a database-backed worker queue**.

The system accepts financial transactions through an API, validates them, processes them asynchronously, maintains customer balances safely under concurrent workers, supports idempotency, retries, crash recovery, and provides an operational React dashboard.

---

## 1. Tech Stack

### Backend

* Python 3.12+
* FastAPI
* SQLAlchemy
* PostgreSQL
* Pydantic
* Alembic
* Uvicorn
* pytest

### Frontend

* React
* TypeScript
* Vite
* Axios

### Database

* PostgreSQL

### Background Processing

A persistent worker queue is implemented using PostgreSQL.

No external queue such as:

* RabbitMQ
* Kafka
* Redis Queue
* AWS SQS

is required.

---

# 2. Project Structure

```text
transaction-processing-system/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── worker.py
│   │
│   ├── alembic/
│   ├── tests/
│   ├── .env
│   ├── .env.example
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
├── .gitignore
└── README.md
```

---

# 3. Prerequisites

Install the following software before starting:

* Python 3.12+
* Node.js 18+
* npm
* PostgreSQL 14+
* Git

Verify the installations:

```bash
python3 --version
node --version
npm --version
psql --version
git --version
```

Example:

```text
Python 3.12.x
Node v20.x
npm 10.x
PostgreSQL 16.x
git 2.x
```

---

# 4. Clone the Repository

```bash
git clone <repository-url>
cd transaction-processing-system
```

---

# 5. PostgreSQL Setup

Create the database:

```sql
CREATE DATABASE transaction_db;
```

Create the application user:

```sql
CREATE USER transaction_user WITH PASSWORD 'transaction_pass';
```

Grant access:

```sql
GRANT ALL PRIVILEGES ON DATABASE transaction_db
TO transaction_user;
```

Connect to the database:

```bash
psql -U transaction_user -d transaction_db
```

If PostgreSQL requires the host explicitly:

```bash
psql -h localhost -U transaction_user -d transaction_db
```

---

# 6. Backend Setup

Open a terminal and go to the backend:

```bash
cd backend
```

## 6.1 Create virtual environment

Linux/macOS:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

---

## 6.2 Install Python dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` does not exist yet:

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic-settings alembic pytest
```

Then:

```bash
pip freeze > requirements.txt
```

---

# 7. Configure Backend Environment

Copy the example environment file:

```bash
cp .env.example .env
```

The `.env` file should contain:

```text
database_url=postgresql+psycopg2://transaction_user:transaction_pass@localhost:5432/transaction_db
```

Update the username, password, host, port, or database name if your PostgreSQL setup is different.

Do not commit `.env` to Git.

---

# 8. Run Database Migrations

From the `backend` directory:

```bash
alembic upgrade head
```

This creates the required tables.

The main tables are:

```text
customers
transactions
worker_jobs
```

---

# 9. Create a Test Customer

Connect to PostgreSQL:

```bash
psql -h localhost -U transaction_user -d transaction_db
```

Run:

```sql
INSERT INTO customers (
    customer_id,
    name,
    balance
)
VALUES (
    'CUST-001',
    'Test Customer',
    5000.00
);
```

Verify:

```sql
SELECT *
FROM customers;
```

You should see:

```text
CUST-001 | Test Customer | 5000.00
```

---

# 10. Start FastAPI Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The API should start at:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
    "status": "healthy",
    "database": "healthy"
}
```

---

# 11. Start the Background Worker

Open a **second terminal**.

Go to the backend:

```bash
cd backend
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

Start the worker:

```bash
python -m app.worker
```

Expected output:

```text
Worker started: <worker-id>
```

The worker continuously checks the PostgreSQL-backed job queue.

---

# 12. Start React Frontend

Open a **third terminal**.

Go to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start Vite:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

Open it in a browser.

---

# 13. Running the Complete Application

The complete local application requires three running processes.

### Terminal 1 — FastAPI

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Terminal 2 — Worker

```bash
cd backend
source venv/bin/activate
python -m app.worker
```

### Terminal 3 — React

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

# 14. Application Flow

```text
                React
                  |
                  | POST /transactions
                  v
              FastAPI
                  |
                  v
            PostgreSQL
             /        \
            /          \
   transactions     worker_jobs
                         |
                         | PENDING
                         v
                      Worker
                         |
                         | PROCESSING
                         v
                 Lock Customer Row
                         |
                         v
                 Validate Balance
                         |
                    +----+----+
                    |         |
                  CREDIT    DEBIT
                    |         |
                    +----+----+
                         |
                         v
                  Update Balance
                         |
                         v
                      SUCCESS
```

---

# 15. Transaction Lifecycle

A transaction normally follows:

```text
PENDING
   |
   v
PROCESSING
   |
   +------------------+
   |                  |
   v                  v
SUCCESS             FAILED
                       |
                       v
                 Automatic Retry
                       |
                       v
                    PENDING
```

After the maximum number of automatic attempts:

```text
FAILED
```

The transaction can also be manually retried by an operator.

---

# 16. API Endpoints

## Health

```http
GET /health
```

Checks application and database health.

---

## Create Transaction

```http
POST /transactions
```

Example:

```json
{
    "transaction_id": "TXN-1001",
    "customer_id": "CUST-001",
    "transaction_type": "DEBIT",
    "amount": 500
}
```

The API returns quickly with a `PENDING` transaction while the worker processes it asynchronously.

---

## Get Transaction

```http
GET /transactions/{transaction_id}
```

Example:

```text
GET /transactions/TXN-1001
```

---

## Get All Transactions

```http
GET /transactions
```

Pagination:

```text
GET /transactions?page=1&page_size=10
```

Status filter:

```text
GET /transactions?status=SUCCESS
```

Transaction type filter:

```text
GET /transactions?transaction_type=DEBIT
```

Combined:

```text
GET /transactions?status=SUCCESS&transaction_type=DEBIT
```

---

## Customer Balance

```http
GET /customers/{customer_id}/balance
```

Example:

```text
GET /customers/CUST-001/balance
```

---

## Customer Transaction History

```http
GET /customers/{customer_id}/transactions
```

Example:

```text
GET /customers/CUST-001/transactions?page=1&page_size=10
```

---

## Manual Retry

```http
POST /transactions/{transaction_id}/retry
```

Example:

```text
POST /transactions/TXN-1001/retry
```

Only eligible failed transactions can be manually retried.

---

# 17. Idempotency

`transaction_id` acts as the idempotency key.

If the same transaction is submitted twice:

```text
TXN-1001
TXN-1001
```

the system does not create a second transaction or worker job.

If the same ID is submitted with different transaction details:

```text
TXN-1001 → DEBIT 500
TXN-1001 → CREDIT 500
```

the API returns:

```text
409 Conflict
```

This prevents accidental duplicate or conflicting financial operations.

---

# 18. Concurrency Safety

Customer balance updates use database row-level locking.

Conceptually:

```text
Worker A                    Worker B

Lock Customer
     |
Read balance
     |
Validate debit
     |
Update balance
     |
Commit
     |
Unlock
                              |
                         Gets customer lock
                              |
                         Reads latest balance
                              |
                         Validates debit
```

This prevents two concurrent workers from both using the same stale balance.

---

# 19. Worker Job Claiming

Multiple workers can safely process jobs using:

```sql
SELECT ...
FROM worker_jobs
WHERE status = 'PENDING'
FOR UPDATE SKIP LOCKED;
```

`SKIP LOCKED` prevents another worker from waiting on a job that has already been claimed.

This allows multiple local workers to operate concurrently.

---

# 20. Crash Recovery

Worker jobs contain:

```text
locked_at
locked_by
status
```

If a worker crashes while processing a job, the job can remain in:

```text
PROCESSING
```

The recovery mechanism identifies stale jobs and moves them back to:

```text
PENDING
```

The system also checks whether the transaction has already reached:

```text
SUCCESS
```

before reprocessing it.

This prevents double application of a financial transaction.

---

# 21. Retry Strategy

Automatic retries are bounded.

Example:

```text
Attempt 1
   |
   | failure
   v
wait 2 seconds

Attempt 2
   |
   | failure
   v
wait 4 seconds

Attempt 3
   |
   | failure
   v
FAILED
```

Business failures such as insufficient balance are not automatically retried because retrying without a balance change would produce the same result.

---

# 22. React Dashboard

The React application provides:

* Transaction submission
* All-transactions table
* Status filtering
* CREDIT/DEBIT filtering
* Pagination
* Transaction status
* Attempt count
* Customer balance
* Customer transaction history
* Failed transaction retry
* Loading states
* Empty states
* API error handling
* Automatic polling for updated transaction status

---

# 23. Running Tests

From the backend:

```bash
pytest -v
```

Concurrency tests can be run with:

```bash
pytest -v tests/test_concurrency.py
```

The important scenarios include:

* Transaction validation
* Duplicate transaction submission
* Conflicting duplicate transaction
* Credit processing
* Debit processing
* Insufficient balance
* Concurrent debit processing
* Retry behavior
* Crash/stale-job recovery
* API error handling
* Rollback behavior

---

# 24. Example End-to-End Test

### Step 1 — Create customer

```sql
INSERT INTO customers (
    customer_id,
    name,
    balance
)
VALUES (
    'CUST-001',
    'Test Customer',
    5000.00
);
```

### Step 2 — Submit transaction

```http
POST /transactions
```

```json
{
    "transaction_id": "TXN-1001",
    "customer_id": "CUST-001",
    "transaction_type": "DEBIT",
    "amount": 500
}
```

### Step 3 — API response

```json
{
    "transaction_id": "TXN-1001",
    "customer_id": "CUST-001",
    "transaction_type": "DEBIT",
    "amount": 500,
    "status": "PENDING",
    "attempts": 0
}
```

### Step 4 — Worker processes job

```text
PENDING
   ↓
PROCESSING
   ↓
SUCCESS
```

### Step 5 — Check balance

```http
GET /customers/CUST-001/balance
```

Expected:

```json
{
    "customer_id": "CUST-001",
    "balance": 4500.00
}
```

---

# 25. Important Local Development Notes

The application is intentionally designed to run completely locally.

Required services:

```text
PostgreSQL
FastAPI
Worker
React
```

No external cloud service or message broker is required.

For a production deployment, the PostgreSQL-backed worker queue could be replaced with a dedicated messaging/queue system such as Kafka, RabbitMQ, SQS, or another managed queue depending on the workload and operational requirements.

The current implementation is intentionally designed to satisfy the local take-home assignment while demonstrating:

* Database transactions
* Idempotency
* Concurrency control
* Row-level locking
* Persistent jobs
* Retry handling
* Crash recovery
* Pagination
* Operational visibility

---

# 26. Quick Start

For someone who already has PostgreSQL, Python, and Node installed:

```bash
# Clone
git clone <repository-url>

cd transaction-processing-system

# Terminal 1
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# Terminal 2
cd backend
source venv/bin/activate
python -m app.worker

# Terminal 3
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

# 27. Security Notes

Do not commit:

```text
.env
database passwords
API keys
credentials
production secrets
```

Use environment variables for sensitive configuration.

The included `.gitignore` prevents `.env` and common local development files from being committed.

---

# 28. Future Improvements

For a production deployment, the following improvements could be considered:

* Dedicated message broker instead of database polling
* Redis/Kafka/RabbitMQ/SQS depending on requirements
* Multiple worker processes/containers
* Distributed tracing
* Prometheus/Grafana metrics
* Structured JSON logging
* Authentication and authorization
* Rate limiting
* API versioning
* Database connection pooling/tuning
* Automated CI/CD
* Docker/Kubernetes deployment
* Dead-letter queue for permanently failed jobs
* Exponential backoff with jitter
* More comprehensive frontend and integration tests

---

# 29. Assignment Design Summary

The system demonstrates the following core requirements:

| Requirement             | Implementation                         |
| ----------------------- | -------------------------------------- |
| Async processing        | PostgreSQL-backed worker               |
| Persistent queue        | `worker_jobs` table                    |
| Idempotency             | Unique `transaction_id`                |
| Duplicate protection    | Idempotency validation + DB constraint |
| Concurrent workers      | `FOR UPDATE SKIP LOCKED`               |
| Balance safety          | Customer row locking                   |
| Atomic financial update | Database transaction                   |
| Retry                   | Bounded attempts + backoff             |
| Crash recovery          | Stale `PROCESSING` job recovery        |
| Manual retry            | Retry API                              |
| Pagination              | Backend pagination                     |
| Filtering               | Status + transaction type              |
| Operational visibility  | React dashboard                        |
| Status updates          | Polling                                |
| Error handling          | API + UI error states                  |
| Database migrations     | Alembic                                |
| Local execution         | PostgreSQL + FastAPI + Worker + React  |

### One important thing before you commit

Because we have been building this step-by-step, I recommend doing a **final consistency pass before pushing to GitHub**. In particular, we should verify that:

```text
README
   ↕
actual file structure
   ↕
requirements.txt
   ↕
Alembic migration
   ↕
SQLAlchemy models
   ↕
FastAPI endpoints
   ↕
worker
   ↕
React API URLs
```

all match exactly.

That will catch things like a missing dependency, wrong import, incorrect migration, or README command that doesn't work on a clean machine.
