import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "@mantine/core/styles.css";
import "./styles/app.css";

import { AppProviders } from "./app/providers";
import { AppRouter } from "./app/router";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppProviders>
        <AppRouter />
      </AppProviders>
    </BrowserRouter>
  </React.StrictMode>
);
