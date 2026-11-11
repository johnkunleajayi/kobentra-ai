import { Link, useNavigate } from "react-router-dom";
import type { Business } from "../business/types";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import { createOpportunity, opportunitiesPath, type Opportunity } from "./api";
import { OpportunityForm } from "./OpportunityForm";

export function OpportunitiesPage({
  business,
  writable,
}: {
  business: Business;
  writable: boolean;
}) {
  const resource = useResource<{ opportunities: Opportunity[] }>(
    opportunitiesPath(business.organization_id),
  );
  const navigate = useNavigate();
  return (
    <>
      <h2>Opportunities</h2>
      <p>
        Private opportunities owned by <strong>{business.name}</strong>. This
        milestone supports a title and status.
      </p>
      {!resource.data ? (
        <ResourceState error={resource.error} retry={resource.retry} />
      ) : (
        <>
          {!resource.data.opportunities.length && (
            <div className="empty">
              <h3>Your next opportunity starts here.</h3>
              <p>No opportunities have been created for this business.</p>
            </div>
          )}
          {resource.data.opportunities.map((opportunity) => (
            <article className="workspace-note" key={opportunity.id}>
              <span className="badge">{opportunity.stage}</span>
              <h3>{opportunity.title}</h3>
              <p>Owned by {business.name}</p>
              <Link
                className="text-link"
                to={`/workspace/${business.organization_id}/opportunities/${opportunity.id}`}
              >
                View opportunity
              </Link>
            </article>
          ))}
        </>
      )}
      {writable && (
        <>
          <h3>Create an opportunity</h3>
          <OpportunityForm
            save={(input) => createOpportunity(business.organization_id, input)}
            onSaved={(result) =>
              navigate(
                `/workspace/${business.organization_id}/opportunities/${result.id}`,
              )
            }
          />
        </>
      )}
    </>
  );
}
