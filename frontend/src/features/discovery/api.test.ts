import { expect, it } from "vitest";
import { discoveryPath } from "./api";
it("binds discovery to one encoded business identifier", () => {
  expect(discoveryPath("a/b")).toBe("/api/businesses/a%2Fb/matches");
});
