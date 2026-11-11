import { afterEach, describe, expect, it, vi } from "vitest";
import { BusinessApiError, listBusinesses, registerBusiness } from "./api";

afterEach(() => vi.unstubAllGlobals());
describe("business API", () => {
  it("sends profile fields as JSON with session credentials", async () => {
    const input = {
      name: "Sample",
      sector: "Trade",
      country: "Ghana",
      goal: "Buy",
    };
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(input), { status: 201 }));
    vi.stubGlobal("fetch", fetch);
    expect(await registerBusiness(input)).toEqual(input);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/businesses"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        cache: "no-store",
        body: JSON.stringify(input),
      }),
    );
  });
  it("reads a multi-business response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response('{"businesses":[]}')),
    );
    expect(await listBusinesses()).toEqual([]);
  });
  it("handles expired sessions without exposing backend details", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response("internal-secret", { status: 401 })),
    );
    await expect(listBusinesses()).rejects.toEqual(new BusinessApiError(401));
  });
});
