import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { WalletProvider } from "./hooks/useWallet";
import { ToastProvider } from "./hooks/useToast";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <WalletProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </WalletProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
);
