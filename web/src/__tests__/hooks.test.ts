/**
 * Tests for the BFF API client and hook utilities.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch } from "../api/client";

/* ------------------------------------------------------------------ */
/*  apiFetch tests                                                     */
/* ------------------------------------------------------------------ */

let fetchSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, "fetch");
});

afterEach(() => {
  fetchSpy.mockRestore();
});

describe("apiFetch", () => {
  it("returns parsed JSON on success", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true, count: 42 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const result = await apiFetch<{ ok: boolean; count: number }>("/api/test");
    expect(result).toEqual({ ok: true, count: 42 });
    expect(fetchSpy).toHaveBeenCalledOnce();
  });

  it("throws on non-OK response", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response("Not Found", { status: 404 }),
    );

    await expect(apiFetch("/api/missing")).rejects.toThrow("API 404");
  });

  it("sends Content-Type header by default", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 }),
    );

    await apiFetch("/api/test");

    const [, init] = fetchSpy.mock.calls[0];
    expect((init as RequestInit).headers).toHaveProperty(
      "Content-Type",
      "application/json",
    );
  });

  it("passes through custom init options", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({}), { status: 200 }),
    );

    await apiFetch("/api/test", { method: "POST", body: '{"a":1}' });

    const [, init] = fetchSpy.mock.calls[0];
    expect((init as RequestInit).method).toBe("POST");
    expect((init as RequestInit).body).toBe('{"a":1}');
  });
});
