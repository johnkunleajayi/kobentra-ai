import { Link, useParams } from "react-router-dom";
import { ResourceState } from "../workspace/ResourceState";
import { useResource } from "../workspace/useResource";
import { dateLabel, type BusinessDetail } from "./types";

export function AdminBusinessDetail() {
  const { businessId = "" } = useParams();
  const resource = useResource<BusinessDetail>(
    `/api/admin/businesses/${encodeURIComponent(businessId)}`,
  );
  if (!resource.data)
    return <ResourceState error={resource.error} retry={resource.retry} />;
  const business = resource.data,
    qualification = business.qualification;
  return (
    <>
      <Link to="/admin/businesses">← Business directory</Link>
      <header className="admin-heading">
        <span className="eyebrow">READ-ONLY BUSINESS RECORD</span>
        <h1>{business.name}</h1>
        <p>
          {business.country} · {business.industry}
        </p>
      </header>
      <section className="admin-panel">
        <h2>Ownership & registration</h2>
        <dl>
          <div>
            <dt>Owners</dt>
            <dd>
              {business.owners.map((o) => o.email).join(", ") || "Not recorded"}
            </dd>
          </div>
          <div>
            <dt>Registered</dt>
            <dd>{dateLabel(business.registered_at)}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{business.business_status.replace(/_/g, " ")}</dd>
          </div>
        </dl>
      </section>
      <section className="admin-panel">
        <h2>Qualification summary</h2>
        <dl>
          <div>
            <dt>Provisional readiness</dt>
            <dd>
              {qualification.readiness.score ?? "Unknown"} ·{" "}
              {qualification.readiness.classification ?? "Not assessed"}
            </dd>
          </div>
          <div>
            <dt>Assessment completeness</dt>
            <dd>{qualification.completeness.percent}%</dd>
          </div>
          <div>
            <dt>Evidence confidence</dt>
            <dd>
              {qualification.confidence.classification.replace(/_/g, " ")}
            </dd>
          </div>
        </dl>
        <p>
          Readiness is not independent verification. No raw assessment answers
          are displayed.
        </p>
        <ul>
          {qualification.gaps.map((g) => (
            <li key={g.code}>
              {g.code.replace(/_/g, " ")}: {g.recommendation}
            </li>
          ))}
        </ul>
      </section>
      <section className="admin-panel">
        <h2>Assessment history</h2>
        <p>Most recent {business.assessment_history_limit} records maximum.</p>
        {business.assessments.length ? (
          <ul>
            {business.assessments.map((a) => (
              <li key={a.id}>
                {a.provider} · {a.status.replace(/_/g, " ")} · Started{" "}
                {dateLabel(a.initiated_at)} · Completed{" "}
                {dateLabel(a.completed_at)}
              </li>
            ))}
          </ul>
        ) : (
          <p>No assessments recorded.</p>
        )}
      </section>
    </>
  );
}
