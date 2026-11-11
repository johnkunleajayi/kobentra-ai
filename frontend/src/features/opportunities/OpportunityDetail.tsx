import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Business } from "../business/types";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import { opportunityPath, updateOpportunity, type Opportunity } from "./api";
import { OpportunityForm } from "./OpportunityForm";

export function OpportunityDetail({
  business,
  writable,
}: {
  business: Business;
  writable: boolean;
}) {
  const { opportunityId = "" } = useParams();
  const resource = useResource<Opportunity>(
    opportunityPath(business.organization_id, opportunityId),
  );
  const [saved, setSaved] = useState<Opportunity | null>(null);
  const [editing, setEditing] = useState(false);
  const record = saved ?? resource.data;
  if (!record)
    return <ResourceState error={resource.error} retry={resource.retry} />;
  return (
    <>
      <Link
        className="text-link"
        to={`/workspace/${business.organization_id}/opportunities`}
      >
        Back to opportunities
      </Link>
      <h2>{record.title}</h2>
      <p>
        Owned by <strong>{business.name}</strong>
      </p>
      <span className="badge">{record.stage}</span>
      {saved && <p role="status">Opportunity saved.</p>}
      {writable && (
        <>
          <p>
            <button className="secondary" onClick={() => setEditing(!editing)}>
              {editing ? "Cancel editing" : "Edit opportunity"}
            </button>
          </p>
          {editing && (
            <OpportunityForm
              initial={record}
              save={(input) =>
                updateOpportunity(business.organization_id, record.id, input)
              }
              onSaved={(result) => {
                setSaved(result);
                setEditing(false);
              }}
            />
          )}
        </>
      )}
    </>
  );
}
