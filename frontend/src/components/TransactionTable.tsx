import { Transaction } from "../types/transaction"

interface Props {
    transactions: Transaction[];
    onSelect: (transaction: Transaction) => void;
}

export default function TransactionTable({
    transactions,
    onSelect,
}: Props) {
    if (transactions.length === 0) {
        return <p>No transactions found.</p>;
    }

    return (
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
                {transactions.map((transaction) => (
                    <tr
                        key={transaction.transaction_id}
                        onClick={() => onSelect(transaction)}
                    >
                        <td>{transaction.transaction_id}</td>
                        <td>{transaction.customer_id}</td>
                        <td>{transaction.transaction_type}</td>
                        <td>{transaction.amount}</td>
                        <td>{transaction.status}</td>
                        <td>{transaction.attempts}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}