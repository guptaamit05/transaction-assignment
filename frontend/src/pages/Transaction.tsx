import { useEffect, useState } from "react";
import {
  getAllTransactions,
} from "../services/api";

import type {
  Transaction,
  TransactionListResponse,
} from "../types/transaction";

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>(
    []
  );

  const [page, setPage] = useState(1);

  const [pageSize] = useState(10);

  const [total, setTotal] = useState(0);

  const [statusFilter, setStatusFilter] = useState("");

  const [typeFilter, setTypeFilter] = useState("");

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");

  const loadTransactions = async () => {
    try {
      setLoading(true);
      setError("");

      const result: TransactionListResponse =
        await getAllTransactions(
          page,
          pageSize,
          statusFilter || undefined,
          typeFilter || undefined
        );

      setTransactions(result.items);
      setTotal(result.total);
    } catch (error: any) {
      console.error(error);

      setError(
        error.response?.data?.detail ||
          "Unable to load transactions"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  loadTransactions();

  // const interval = setInterval(() => {
  //   loadTransactions();
  // }, 3000);

  // return () => {
  //   clearInterval(interval);
  // };
// }, [page, statusFilter, typeFilter]);
}, []);

  const totalPages = Math.ceil(total / pageSize);

  const handleStatusChange = (
    value: string
  ) => {
    setStatusFilter(value);
    setPage(1);
  };

  const handleTypeChange = (
    value: string
  ) => {
    setTypeFilter(value);
    setPage(1);
  };

  return (
    <div>
      <h1>All Transactions</h1>

      {/* Filters */}
      <div>
        <label>
          Status:

          <select
            value={statusFilter}
            onChange={(e) =>
              handleStatusChange(e.target.value)
            }
          >
            <option value="">All</option>
            <option value="PENDING">Pending</option>
            <option value="PROCESSING">
              Processing
            </option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed</option>
          </select>
        </label>

        <label>
          Transaction Type:

          <select
            value={typeFilter}
            onChange={(e) =>
              handleTypeChange(e.target.value)
            }
          >
            <option value="">All</option>
            <option value="CREDIT">Credit</option>
            <option value="DEBIT">Debit</option>
          </select>
        </label>
      </div>

      {/* Error */}
      {error && (
        <div>
          <p>{error}</p>

          <button onClick={loadTransactions}>
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <p>Loading transactions...</p>
      )}

      {/* Empty */}
      {!loading &&
        !error &&
        transactions.length === 0 && (
          <p>No transactions found.</p>
        )}

      {/* Table */}
      {!loading &&
        !error &&
        transactions.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Customer</th>
                <th>Type</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Attempts</th>
              </tr>
            </thead>

            <tbody>
              {transactions.map(
                (transaction) => (
                  <tr
                    key={
                      transaction.transaction_id
                    }
                  >
                    <td>
                      {transaction.transaction_id}
                    </td>

                    <td>
                      {transaction.customer_id}
                    </td>

                    <td>
                      {transaction.transaction_type}
                    </td>

                    <td>
                      ₹{transaction.amount}
                    </td>

                    <td>
                      {transaction.status}
                    </td>

                    <td>
                      {transaction.attempts}
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}

      {/* Pagination */}
      {!loading &&
        !error &&
        total > 0 && (
          <div>
            <button
              disabled={page === 1}
              onClick={() =>
                setPage((current) => current - 1)
              }
            >
              Previous
            </button>

            <span>
              {" "}
              Page {page} of {totalPages}{" "}
            </span>

            <button
              disabled={page >= totalPages}
              onClick={() =>
                setPage((current) => current + 1)
              }
            >
              Next
            </button>
          </div>
        )}
    </div>
  );
}