import { Link, Navigate } from "react-router-dom";
import type { Business } from "../business/types";
import { useResource } from "./useResource";
import { ResourceState } from "./ResourceState";

export function BusinessSelection() {
  const { data, error, retry } = useResource<{ businesses: Business[] }>(
    "/api/businesses",
  );
  if (!data)
    return (
      <section className="section">
        <h1>Your workspaces</h1>
        <ResourceState error={error} retry={retry} />
      </section>
    );
  if (data.businesses.length === 1)
    return (
      <Navigate
        replace
        to={`/workspace/${data.businesses[0].organization_id}`}
      />
    );
  return (
    <section className="section">
      <span className="eyebrow">YOUR BUSINESSES</span>
      <h1>Choose your workspace.</h1>
      {!data.businesses.length && (
        <p>Register a business to open a workspace.</p>
      )}
      <div className="real-workspace-grid">
        {data.businesses.map((business) => (
          <article className="workspace-note" key={business.organization_id}>
            <h2>{business.name}</h2>
            <p>
              {business.sector} · {business.country}
            </p>
            <Link
              className="button"
              to={`/workspace/${business.organization_id}`}
            >
              Open workspace
            </Link>
          </article>
        ))}
      </div>
      <Link className="text-link" to="/business/onboarding">
        Register another business
      </Link>
      {" · "}
      <Link className="text-link" to="/account">
        My account
      </Link>
    </section>
  );
}
