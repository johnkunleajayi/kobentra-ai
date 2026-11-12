import { useEffect, useState } from "react";
import { jsonWrite, workspaceRequest } from "../workspace/api";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import type { DeletionPreview, DeletionStatus } from "./deletion-types";
import { DeleteBusinessDialog } from "./DeleteBusinessDialog";

export function BusinessDeletion({
  businessId,
  pending,
  completed,
}: {
  businessId: string;
  pending: () => void;
  completed: () => void;
}) {
  const path = `/api/admin/businesses/${encodeURIComponent(businessId)}/deletion`;
  const resource = useResource<DeletionStatus>(path);
  const [preview, setPreview] = useState<DeletionPreview | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const operation = resource.data?.operation;
  useEffect(() => {
    if (
      operation?.state === "completed" &&
      operation.local_data_removed &&
      operation.completed_at &&
      ["not_linked", "recycled_verified"].includes(operation.salesforce_outcome)
    )
      completed();
    else if (operation) pending();
  }, [operation, pending, completed]);
  async function review() {
    setBusy(true);
    setError("");
    try {
      setPreview(await workspaceRequest<DeletionPreview>(path + "/preview"));
    } catch {
      setError(
        "Deletion preview is unavailable. Resolve unsettled dispatches, multiple Lead links, permissions or linkage conflicts before trying again.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function retry() {
    if (!operation) return;
    setBusy(true);
    setError("");
    try {
      await workspaceRequest(
        path + "/retry",
        jsonWrite("POST", { operation_id: operation.id }),
      );
      resource.retry();
    } catch {
      setError(
        "Deletion is not confirmed. Local data remains protected; refresh status and retry when the underlying service is available.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="admin-panel admin-delete-panel">
      <h2>Delete business</h2>
      <p>
        Permanently remove business-owned Kobentra data only after the linked
        Salesforce outcome is verified. This does not delete user accounts.
      </p>
      {!resource.data ? (
        <ResourceState error={resource.error} retry={resource.retry} />
      ) : operation ? (
        <>
          <p role="status">
            Deletion status:{" "}
            <strong>
              {operation.state === "awaiting_permanent_purge"
                ? "pending Recycle Bin revalidation"
                : operation.state.replace(/_/g, " ")}
            </strong>
          </p>
          <p>Operation: {operation.id}</p>
          <p>
            {operation.local_data_removed
              ? "Local data removal verified."
              : "Local data retained. Normal business operations are blocked."}
          </p>
          {operation.error_code && (
            <p role="alert">
              {operation.state === "awaiting_permanent_purge"
                ? "This legacy operation must revalidate the exact linked Lead. Resume deletion to verify Recycle Bin status and continue local cleanup."
                : "The external operation is unavailable or its identity could not be verified. Review linkage, org configuration and permissions before retrying."}
            </p>
          )}
          <button
            className="secondary"
            onClick={resource.retry}
            disabled={busy}
          >
            Refresh deletion status
          </button>
          {operation.state !== "completed" && (
            <button className="secondary" onClick={retry} disabled={busy}>
              {busy ? "Checking…" : "Resume deletion"}
            </button>
          )}
          <ol>
            {operation.events.map((item, index) => (
              <li key={`${item.created_at}-${index}`}>
                {item.state.replace(/_/g, " ")} ·{" "}
                {new Date(item.created_at).toLocaleString()}
              </li>
            ))}
          </ol>
        </>
      ) : (
        <button
          className="button admin-destructive"
          onClick={review}
          disabled={busy}
        >
          {busy ? "Preparing preview…" : "Delete business"}
        </button>
      )}
      {error && <p role="alert">{error}</p>}
      {preview && (
        <DeleteBusinessDialog
          businessId={businessId}
          preview={preview}
          close={() => {
            setPreview(null);
            resource.retry();
          }}
          confirmed={() => {
            setPreview(null);
            pending();
            resource.retry();
          }}
        />
      )}
    </section>
  );
}
