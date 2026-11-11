import { afterEach, expect, it, vi } from "vitest";
import { businessPath, jsonWrite, workspaceRequest } from "./api";

afterEach(() => vi.unstubAllGlobals());
it("binds a write to the selected stable business path and cookie session", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response('{"preferences":[]}'));
  vi.stubGlobal("fetch", fetch);
  await workspaceRequest(
    `${businessPath("org-a")}/market-preferences`,
    jsonWrite("PUT", { preferences: [] }),
  );
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining("/api/businesses/org-a/market-preferences"),
    expect.objectContaining({
      credentials: "include",
      method: "PUT",
      cache: "no-store",
    }),
  );
});
it("does not surface raw database error details", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response("private database detail", { status: 503 }),
      ),
  );
  await expect(workspaceRequest("/api/businesses/org-a")).rejects.toThrow(
    "Unable to complete",
  );
});
it("encodes business identifiers as a single path component", () => {
  expect(businessPath("a/b")).toBe("/api/businesses/a%2Fb");
});
