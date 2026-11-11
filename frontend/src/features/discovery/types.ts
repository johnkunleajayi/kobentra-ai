export interface PartnerMatch {
  partner: {
    business_id: string;
    name: string;
    sector: string;
    country: string;
  };
  compatibility: {
    rules_version: string;
    score: number | null;
    coverage_percent: number;
    sufficient_evidence: boolean;
    provisional: boolean;
    limitations: string[];
    dimensions: {
      dimension: string;
      state: "compatible" | "incompatible" | "unknown";
      reason: string;
      weight: number;
      known_weight: number;
      score: number | null;
    }[];
  };
  qualification_gaps: string[];
  introduction_eligibility: {
    allowed: boolean;
    missing_verifications: string[];
    reason: string;
  };
}
export interface DiscoveryResponse {
  business_id: string;
  rules_version: string;
  directory_status: "curated_allowlist" | "not_configured";
  matches: PartnerMatch[];
  requester_qualification_gaps: { code: string; recommendation: string }[];
}
