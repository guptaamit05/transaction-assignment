import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transaction"
import TransactionForm from "./components/TransactionForm";

function App() {
  return (
    <div>
      <Dashboard />

      <hr />

      <TransactionForm />

      <hr />

      <Transactions />
    </div>
  );
}

export default App;