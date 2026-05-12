import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Global error interceptor
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);

export default client;