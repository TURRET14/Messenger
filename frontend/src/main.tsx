import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { DialogsProvider } from "./context/DialogsContext";
import { ThemeProvider } from "./theme/ThemeContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <DialogsProvider>
        <App />
      </DialogsProvider>
    </ThemeProvider>
  </StrictMode>,
);
