/**
 * Shared test utilities — render wrapper with providers.
 */

import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ShellProvider } from "../shell/ShellProvider";

/** Create a fresh QueryClient for each test to avoid shared state. */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

/** Wraps children in all required providers (QueryClient + ShellProvider). */
function AllProviders({ children }: { children: ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <ShellProvider>{children}</ShellProvider>
    </QueryClientProvider>
  );
}

/** Custom render that wraps the component in providers. */
function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Re-export everything from testing-library so tests import from one place
export * from "@testing-library/react";
export { renderWithProviders as render };
