import { useEffect, useRef, useState } from "react";
import { jsonWrite, workspaceRequest } from "../workspace/api";
import type { DeletionPreview, DeletionStatus } from "./deletion-types";

export function DeleteBusinessDialog({
  businessId,
  preview,
  close,
  confirmed,
}: {
  businessId: string;
  preview: DeletionPreview;
  close: () => void;
  confirmed: (value: DeletionStatus) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const key = useRef(crypto.randomUUID());
  const payload = useRef<string | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "").trim(),
      reason = String(form.get("reason") || "").trim();
    if (name !== preview.business_name || !reason) {
      setError("Enter the exact business name and a reason.");
      return;
    }
    const body = {
      business_name: name,
      reason,
      expected_version: preview.version,
      preview_token: preview.preview_token,
      request_id: key.current,
    };
    if (payload.current && payload.current !== JSON.stringify(body)) {
      key.current = crypto.randomUUID();
      body.request_id = key.current;
    }
    payload.current = JSON.stringify(body);
    setBusy(true);
    try {
      confirmed(
        await workspaceRequest<DeletionStatus>(
          `/api/admin/businesses/${encodeURIComponent(businessId)}/deletion`,
          jsonWrite("POST", body),
        ),
      );
    } catch {
      setError(
        "Deletion was not confirmed. Check operation status before retrying. If the preview changed, cancel and review it again.",
      );
    } finally {
      setBusy(false);
    }
  }
  const blocked =
    !!preview.salesforce_target && !preview.salesforce_deletion_enabled;
  return (
    <dialog
      ref={dialog}
      className="admin-dialog"
      aria-labelledby="delete-business-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) close();
      }}
    >
      <h2 id="delete-business-title">Delete Kobentra business</h2>
      <p>
        This cannot be undone locally. User accounts and required platform audit
        history will remain.
      </p>
      <p>
        The exact linked Salesforce Lead will be moved to the recoverable
        Salesforce Recycle Bin. Kobentra business-owned data will be removed
        under the local cleanup policy.
      </p>
      <strong>{preview.business_name}</strong>
      <dl>
        {Object.entries(preview.dependencies).map(([table, count]) => (
          <div key={table}>
            <dt>{table.replace(/_/g, " ")}</dt>
            <dd>{count}</dd>
          </div>
        ))}
      </dl>
      {preview.salesforce_target && (
        <p>
          Linked Lead: {preview.salesforce_target.lead_id} · Org:{" "}
          {preview.salesforce_target.org_id}
        </p>
      )}
      <ul>
        {preview.implications.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      {blocked && (
        <p role="alert">
          Salesforce Recycle Bin deletion is disabled by server configuration.
          Confirmation is blocked; no deletion will be started.
        </p>
      )}
      <form onSubmit={submit}>
        <fieldset disabled={busy || blocked}>
          <label>
            Type the business name exactly
            <input name="name" required maxLength={100} autoComplete="off" />
          </label>
          <label>
            Required deletion reason
            <textarea name="reason" required maxLength={2000} />
          </label>
          <small>
            Do not include secrets or personal identity documents in the audit
            reason.
          </small>
          {error && <p role="alert">{error}</p>}
          <button className="button admin-destructive" type="submit">
            {busy ? "Starting deletion…" : "Confirm business deletion"}
          </button>
        </fieldset>
      </form>
      {error && (
        <button
          className="secondary"
          type="button"
          disabled={busy}
          onClick={close}
        >
          Check deletion status
        </button>
      )}
      <button
        className="secondary"
        type="button"
        disabled={busy}
        onClick={close}
      >
        Cancel
      </button>
    </dialog>
  );
}
