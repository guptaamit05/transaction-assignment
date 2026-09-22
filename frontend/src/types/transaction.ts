export type TransactionType = "CREDIT" | "DEBIT";

export type TransactionStatus =
  | "PENDING"
  | "PROCESSING"
  | "SUCCESS"
  | "FAILED";

export interface Transaction {
  transaction_id: string;
  customer_id: string;
  transaction_type: TransactionType;
  amount: number;
  status: TransactionStatus;
  attempts: number;
}

export interface TransactionListResponse {
  items: Transaction[];
  page: number;
  page_size: number;
  total: number;
}

export interface CustomerBalance {
  customer_id: string;
  balance: number;
}