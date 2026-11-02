import { describe, it, expect } from "vitest";
import { filterMatches } from "./data";
describe("demo discovery", () => {
  it("combines country and text filters", () => {
    expect(filterMatches("distributor", "Ghana")).toHaveLength(1);
    expect(filterMatches("distributor", "Nigeria")).toHaveLength(0);
  });
  it("normalizes query whitespace and case", () =>
    expect(filterMatches(" TERRA ", "All markets")[0].id).toBe("demo-2"));
});
