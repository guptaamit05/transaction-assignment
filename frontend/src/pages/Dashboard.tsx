import { useEffect, useState } from "react";
import {
  getCustomerTransactions,
} from "../services/api";

export default function Dashboard() {
  const [transactions, setTransactions] = useState<any[]>(
    []
  );

  const loadTransactions = async () => {
    try {
      const result =
        await getCustomerTransactions(
          "CUST-001",
          1,
          100
        );

      setTransactions(result.items);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    loadTransactions();

    // const interval = setInterval(
    //   loadTransactions,
    //   3000
    // );

    // return () => clearInterval(interval);
  }, []);

  const pending = transactions.filter(
    (t) => t.status === "PENDING"
  ).length;

  const processing = transactions.filter(
    (t) => t.status === "PROCESSING"
  ).length;

  const success = transactions.filter(
    (t) => t.status === "SUCCESS"
  ).length;

  const failed = transactions.filter(
    (t) => t.status === "FAILED"
  ).length;

  return (
    <div>
      <h1>Transaction Dashboard</h1>

      <div>
        <div>
          <h3>Pending</h3>
          <p>{pending}</p>
        </div>

        <div>
          <h3>Processing</h3>
          <p>{processing}</p>
        </div>

        <div>
          <h3>Success</h3>
          <p>{success}</p>
        </div>

        <div>
          <h3>Failed</h3>
          <p>{failed}</p>
        </div>
      </div>
    </div>
  );
}