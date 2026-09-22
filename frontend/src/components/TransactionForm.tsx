import { FormEvent, useState } from "react";
import { createTransaction } from "../services/api";

export default function TransactionForm() {
  const [transactionId, setTransactionId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [type, setType] = useState<"CREDIT" | "DEBIT">("CREDIT");
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();

    if (!transactionId || !customerId || !amount) {
      setMessage("Please fill all required fields");
      return;
    }

    const numericAmount = Number(amount);

    if (numericAmount <= 0) {
      setMessage("Amount must be greater than 0");
      return;
    }

    try {
      setLoading(true);
      setMessage("");

      const result = await createTransaction({
        transaction_id: transactionId,
        customer_id: customerId,
        transaction_type: type,
        amount: numericAmount,
      });

      setMessage(
        `Transaction ${result.transaction_id} created`
      );

      setTransactionId("");
      setAmount("");
    } catch (error: any) {
      setMessage(
        error.response?.data?.detail ||
          "Failed to create transaction"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Create Transaction</h2>

      <input
        placeholder="Transaction ID"
        value={transactionId}
        onChange={(e) =>
          setTransactionId(e.target.value)
        }
      />

      <input
        placeholder="Customer ID"
        value={customerId}
        onChange={(e) =>
          setCustomerId(e.target.value)
        }
      />

      <select
        value={type}
        onChange={(e) =>
          setType(
            e.target.value as "CREDIT" | "DEBIT"
          )
        }
      >
        <option value="CREDIT">Credit</option>
        <option value="DEBIT">Debit</option>
      </select>

      <input
        type="number"
        min="0.01"
        step="0.01"
        placeholder="Amount"
        value={amount}
        onChange={(e) =>
          setAmount(e.target.value)
        }
      />

      <button type="submit" disabled={loading}>
        {loading ? "Submitting..." : "Submit Transaction"}
      </button>

      {message && <p>{message}</p>}
    </form>
  );
}