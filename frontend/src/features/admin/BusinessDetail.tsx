import { Link, useParams } from "react-router-dom";
import { useCallback, useState } from "react";
import { ResourceState } from "../workspace/ResourceState";
import { useResource } from "../workspace/useResource";
import { dateLabel, type BusinessDetail } from "./types";
import { BusinessManagement } from "./BusinessManagement";
import { BusinessDeletion } from "./BusinessDeletion";

export function AdminBusinessDetail() {
  const { businessId = "" } = useParams();
  const [savedBusiness, setSavedBusiness] = useState("");
  const [deletingBusiness, setDeletingBusiness] = useState("");
  const [deletedBusiness, setDeletedBusiness] = useState("");
  const deletionPending = useCallback(
    () => setDeletingBusiness(businessId),
    [businessId],
  );
  const deletionCompleted = useCallback(
    () => setDeletedBusiness(businessId),
    [businessId],
  );
  const resource = useResource<BusinessDetail>(
    `/api/admin/businesses/${encodeURIComponent(businessId)}`,
  );
  if (!resource.data)
    return <ResourceState error={resource.error} retry={resource.retry} />;
  if (deletedBusiness === businessId)
    return (
      <section className="admin-panel">
        <h1>Business deletion completed</h1>
        <p>
          Business-owned local data was removed after linked Lead Recycle Bin
          deletion was verified or no Lead was linked. Required platform audit
          history remains.
        </p>
        <Link to="/admin/businesses">Return to business directory</Link>
      </section>
    );
  const business = resource.data,
    qualification = business.qualification;
  return (
    <>
      <Link to="/admin/businesses">← Business directory</Link>
      <header className="admin-heading">
        <span className="eyebrow">BUSINESS ADMINISTRATION</span>
        <h1>{business.name}</h1>
        <p>
          {business.country} · {business.industry}
        </p>
      </header>
      {savedBusiness === businessId && (
        <p role="status">Administrative decision saved.</p>
      )}
      <BusinessManagement
        disabled={deletingBusiness === businessId}
        key={`management-${businessId}`}
        business={business}
        refresh={() => {
          setSavedBusiness(businessId);
          resource.retry();
        }}
      />
      <BusinessDeletion
        key={`deletion-${businessId}`}
        businessId={businessId}
        pending={deletionPending}
        completed={deletionCompleted}
      />
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
