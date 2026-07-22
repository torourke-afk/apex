import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ShellProvider } from "./shell/ShellProvider";
import { AppShell } from "./shell/AppShell";
import "./globals.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ShellProvider>
        <AppShell />
      </ShellProvider>
    </QueryClientProvider>
  </StrictMode>,
);
