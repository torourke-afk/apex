/**
 * Vitest global test setup.
 *
 * - Extends matchers with @testing-library/jest-dom
 * - Stubs browser APIs not available in jsdom
 */

import "@testing-library/jest-dom/vitest";

// Stub ResizeObserver (used by some chart / layout components)
globalThis.ResizeObserver ??= class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Stub matchMedia (used by theme detection)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Stub IntersectionObserver (used by lazy-loading patterns)
globalThis.IntersectionObserver ??= class IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds: readonly number[] = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
} as any;
