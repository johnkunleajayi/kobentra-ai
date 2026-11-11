import { Link } from "react-router-dom";
import type { Business } from "./types";

export function BusinessSummary({ business }: { business: Business }) {
  return (
    <article className="workspace-note">
      <span className="eyebrow">REGISTERED BUSINESS · {business.role}</span>
      <h2 style={{ fontSize: "2rem" }}>{business.name}</h2>
      <p>
        {business.sector} · {business.country}
      </p>
      <p style={{ overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>
        {business.goal}
      </p>
      <Link className="button" to={`/workspace/${business.organization_id}`}>Open workspace</Link>
    </article>
  );
}
