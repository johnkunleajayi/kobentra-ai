import { ArrowUpRight, MapPin } from "lucide-react";
import type { PartnerMatch } from "./types";

const labels: Record<string, string> = {
  intent: "Partnership intent",
  industry_capability: "Industry & capability",
  geography: "Geographic fit",
  operations: "Operational suitability",
  timing: "Partnership timing",
};

export function PartnerCard({
  match,
  sourceCountry,
}: {
  match: PartnerMatch;
  sourceCountry: string;
}) {
  const { partner, compatibility: fit } = match;
  const fictional = partner.name.startsWith("Fictional Demo — ");
  const scored = fit.score !== null && fit.sufficient_evidence;
  return (
    <article className="partner-card" aria-label={partner.name}>
      <div className="partner-route">
        <span>{sourceCountry}</span>
        <ArrowUpRight aria-hidden="true" size={20} />
        <span>{partner.country}</span>
      </div>
      <div className="partner-card-top">
        <div>
          <span className="discovery-kicker">
            {fictional ? "FICTIONAL DEMO BUSINESS" : "PROVISIONAL DISCOVERY"}
          </span>
          <h3>{partner.name}</h3>
          <p className="partner-location">
            <MapPin size={15} aria-hidden="true" />
            {partner.country} · {partner.sector}
          </p>
        </div>
        <div className="partner-score">
          <strong>{scored ? `${fit.score}` : "—"}</strong>
          <span>{scored ? "Compatibility / 100" : "Not enough evidence"}</span>
        </div>
      </div>
      <div className="partner-coverage">
        <span>
          Evidence coverage <strong>{fit.coverage_percent}%</strong>
        </span>
        <meter
          aria-label="Evidence coverage"
          min={0}
          max={100}
          value={fit.coverage_percent}
        />
        <small>
          Coverage reflects how much of this match can be explained from
          declared information.
        </small>
      </div>
      <details className="partner-explanation" open>
        <summary>Why this business appears</summary>
        <ul>
          {fit.dimensions.map((d) => (
            <li key={d.dimension}>
              <div>
                <strong>{labels[d.dimension] ?? d.dimension}</strong>
                <span className={`dimension-state ${d.state}`}>{d.state}</span>
              </div>
              <p>{d.reason}</p>
            </li>
          ))}
        </ul>
      </details>
      <details className="partner-explanation">
        <summary>Evidence limitations & qualification gaps</summary>
        <ul>
          {[...new Set([...fit.limitations, ...match.qualification_gaps])].map(
            (text) => (
              <li key={text}>{text}</li>
            ),
          )}
        </ul>
      </details>
      <p className="partner-guard">
        Potential partner, not a verified commercial relationship. Introductions
        remain a separate consent-based step.
      </p>
    </article>
  );
}
