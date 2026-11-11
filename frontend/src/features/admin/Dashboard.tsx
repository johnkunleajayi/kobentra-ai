import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import type { Dashboard } from "./types";

export function AdminDashboard() {
  const resource = useResource<Dashboard>("/api/admin/dashboard");
  return (
    <>
      <header className="admin-heading">
        <span className="eyebrow">PLATFORM OVERVIEW</span>
        <h1>
          A clearer view
          <br />
          of the network.
        </h1>
        <p>
          Registered activity, assessed with context. Platform-wide reads are
          restricted to the owner.
        </p>
      </header>
      {!resource.data ? (
        <ResourceState error={resource.error} retry={resource.retry} />
      ) : (
        <>
          <div className="admin-stats">
            {(
              [
                ["Registered users", resource.data.users],
                ["Businesses", resource.data.businesses],
                ["Workspaces", resource.data.workspaces],
              ] as const
            ).map(([label, value]) => (
              <article key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>
          <div className="admin-summary-grid">
            <section className="admin-panel">
              <h2>Assessment activity</h2>
              {Object.keys(resource.data.assessment_statuses).length ? (
                <dl>
                  {Object.entries(resource.data.assessment_statuses).map(
                    ([status, count]) => (
                      <div key={status}>
                        <dt>{status.replace(/_/g, " ")}</dt>
                        <dd>{count}</dd>
                      </div>
                    ),
                  )}
                </dl>
              ) : (
                <p>No assessments recorded.</p>
              )}
            </section>
            <section className="admin-panel">
              <h2>Qualification evidence</h2>
              <strong className="admin-evidence-count">
                {resource.data.qualification.self_reported_snapshots}
              </strong>
              <p>
                Self-reported evidence snapshots. This count does not imply
                independent business verification.
              </p>
              <p>
                Independent verification:{" "}
                {resource.data.qualification.independent_verification.replace(
                  /_/g,
                  " ",
                )}
              </p>
            </section>
          </div>
          <p className="admin-note">
            Each organization is one workspace. Business profiles and workspaces
            are counted separately; these are not additive measures of unique
            companies.
          </p>
        </>
      )}
    </>
  );
}
