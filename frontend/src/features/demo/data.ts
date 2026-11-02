import type { Match } from "../contracts";
export const matches: Match[] = [
  {
    id: "demo-1",
    name: "Akora Distribution",
    country: "Ghana",
    sector: "Food & agriculture",
    kind: "Distributor",
    explanation:
      "Illustrative fit: a shared interest in packaged foods and distribution in Ghana. This is a sample explanation, not an AI evaluation.",
    initials: "AD",
  },
  {
    id: "demo-2",
    name: "Terra Packaging",
    country: "Nigeria",
    sector: "Manufacturing",
    kind: "Supplier",
    explanation:
      "Illustrative fit: packaging supply for manufacturers in Nigeria. No availability or business verification has been performed.",
    initials: "TP",
  },
  {
    id: "demo-3",
    name: "Baobab Market Collective",
    country: "Senegal",
    sector: "Retail & trade",
    kind: "Buyer",
    explanation:
      "Illustrative fit: retail market access in Senegal. This fictional business has no real contact details.",
    initials: "BM",
  },
];
export function filterMatches(query: string, country: string) {
  return matches.filter(
    (m) =>
      (country === "All markets" || m.country === country) &&
      `${m.name} ${m.sector} ${m.kind}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
}
