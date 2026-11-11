import { useEffect, useRef, useState } from "react";
import { jsonWrite, workspaceRequest } from "../workspace/api";
import type { AdminAction, EditableProfile } from "./management-types";

export function DecisionDialog({
  action,
  businessId,
  version,
  profile,
  close,
  saved,
}: {
  action: AdminAction;
  businessId: string;
  version: number;
  profile: EditableProfile;
  close: () => void;
  saved: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const requestId = useRef(crypto.randomUUID());
  const retryBody = useRef<string | null>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const fields = new FormData(event.currentTarget);
    const body: Record<string, unknown> = {
      request_id: requestId.current,
      expected_version: version,
      reason: String(fields.get("reason") || "").trim(),
    };
    if (!body.reason) {
      setError("A decision reason is required.");
      return;
    }
    if (action === "edit_profile")
      body.profile = Object.fromEntries(
        ["name", "sector", "country", "goal"].map((key) => [
          key,
          String(fields.get(key) || "").trim(),
        ]),
      );
    else {
      body.action = action;
      body.evidence_references =
        action === "verify_identity"
          ? String(fields.get("references") || "")
              .split("\n")
              .map((s) => s.trim())
              .filter(Boolean)
          : [];
    }
    const serialized = JSON.stringify(body);
    if (retryBody.current !== serialized) {
      requestId.current = crypto.randomUUID();
      body.request_id = requestId.current;
      retryBody.current = JSON.stringify(body);
    }
    setBusy(true);
    try {
      await workspaceRequest(
        `/api/admin/businesses/${encodeURIComponent(businessId)}/${action === "edit_profile" ? "profile" : "decisions"}`,
        jsonWrite(action === "edit_profile" ? "PUT" : "POST", body),
      );
      saved();
    } catch {
      setError(
        "Decision was not confirmed. Retry unchanged for a safe replay, or cancel and reload if the record changed.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="admin-dialog"
      aria-labelledby="decision-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) close();
      }}
    >
      <h2 id="decision-title">Confirm {action.replace(/_/g, " ")}</h2>
      <p>
        This decision will be recorded with your administrator identity and
        timestamp.
      </p>
      {action === "edit_profile" && (
        <p>
          Changing name or country resets identity verification and approval to
          pending. Salesforce records will not be updated.
        </p>
      )}
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          {action === "edit_profile" &&
            (
              [
                ["name", "Business name", 100],
                ["sector", "Industry / sector", 100],
                ["country", "Country", 80],
                ["goal", "Business description / goal", 500],
              ] as const
            ).map(([key, label, max]) => (
              <label key={key}>
                <span id={`admin-profile-label-${key}`}>{label}</span>
                {key === "goal" ? (
                  <textarea
                    aria-labelledby={`admin-profile-label-${key}`}
                    name={key}
                    defaultValue={profile[key]}
                    required
                    maxLength={max}
                  />
                ) : (
                  <input
                    aria-labelledby={`admin-profile-label-${key}`}
                    name={key}
                    defaultValue={profile[key]}
                    required
                    maxLength={max}
                  />
                )}
              </label>
            ))}
          {action === "verify_identity" && (
            <label>
              Independent evidence references (one per line)
              <textarea name="references" required maxLength={5000} />
              <small>
                Reference existing independently reviewed evidence. Do not enter
                credentials or raw identity documents.
              </small>
            </label>
          )}
          <label>
            Required decision reason
            <textarea name="reason" required maxLength={2000} />
          </label>
          {error && <p role="alert">{error}</p>}
          <div className="admin-dialog-actions">
            <button className="secondary" type="button" onClick={close}>
              Cancel
            </button>
            <button className="button" type="submit">
              {busy ? "Saving…" : "Confirm decision"}
            </button>
          </div>
        </fieldset>
      </form>
    </dialog>
  );
}
