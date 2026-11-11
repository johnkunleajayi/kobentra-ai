import { useState } from "react";
import { ResourceState } from "../workspace/ResourceState";
import { useResource } from "../workspace/useResource";
import type { HistoryPage } from "./management-types";

export function DecisionHistory({ businessId }: { businessId: string }) {
  const [page, setPage] = useState(1);
  const resource = useResource<HistoryPage>(
    `/api/admin/businesses/${encodeURIComponent(businessId)}/history?page=${page}`,
  );
  return (
    <section className="admin-panel">
      <h2>Administrative decision history</h2>
      {!resource.data ? (
        <ResourceState error={resource.error} retry={resource.retry} />
      ) : (
        <>
          {!resource.data.items.length ? (
            <p>No administrative decisions recorded.</p>
          ) : (
            <ol className="admin-history">
              {resource.data.items.map((item) => (
                <li key={item.id}>
                  <strong>{item.action.replace(/_/g, " ")}</strong>
                  <p>
                    {new Date(item.created_at).toLocaleString()} · Administrator{" "}
                    {item.actor_id}
                  </p>
                  <p>{item.reason}</p>
                  {item.evidence_references.length > 0 && (
                    <p>
                      Evidence references: {item.evidence_references.join("; ")}
                    </p>
                  )}
                  <details>
                    <summary>Previous and new values</summary>
                    <pre>
                      {JSON.stringify(
                        {
                          previous: item.previous_values,
                          new: item.new_values,
                        },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                </li>
              ))}
            </ol>
          )}
          <nav
            className="admin-pagination"
            aria-label="Decision history pagination"
          >
            <button
              className="secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous decisions
            </button>
            <span>Page {page}</span>
            <button
              className="secondary"
              disabled={page * 20 >= resource.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next decisions
            </button>
          </nav>
        </>
      )}
    </section>
  );
}
