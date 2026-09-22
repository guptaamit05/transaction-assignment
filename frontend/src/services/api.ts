import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

export const getTransaction = async (
  transactionId: string
) => {
  const response = await api.get(
    `/transactions/${transactionId}`
  );

  return response.data;
};

export const createTransaction = async (data: {
  transaction_id: string;
  customer_id: string;
  transaction_type: "CREDIT" | "DEBIT";
  amount: number;
}) => {
  const response = await api.post(
    "/transactions",
    data
  );

  return response.data;
};

export const retryTransaction = async (
  transactionId: string
) => {
  const response = await api.post(
    `/transactions/${transactionId}/retry`
  );

  return response.data;
};

export const getCustomerBalance = async (
  customerId: string
) => {
  const response = await api.get(
    `/customers/${customerId}/balance`
  );

  return response.data;
};

export const getCustomerTransactions = async (
  customerId: string,
  page = 1,
  pageSize = 10,
  status?: string,
  transactionType?: string
) => {
  const response = await api.get(
    `/customers/${customerId}/transactions`,
    {
      params: {
        page,
        page_size: pageSize,
        status,
        transaction_type: transactionType,
      },
    }
  );

  return response.data;
};



export const getAllTransactions = async (
  page = 1,
  pageSize = 10,
  status?: string,
  transactionType?: string
) => {
  const response = await api.get("/transactions", {
    params: {
      page,
      page_size: pageSize,
      status: status || undefined,
      transaction_type: transactionType || undefined,
    },
  });

  return response.data;
};


export default api;