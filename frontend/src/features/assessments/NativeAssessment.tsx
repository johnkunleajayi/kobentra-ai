import { useEffect, useRef, useState } from "react";
import { assessmentsPath, initiateAssessment, type Assessment } from "./api";
import { jsonWrite, workspaceRequest } from "../workspace/api";

export function NativeAssessment({
  businessId,
  assessments,
  refresh,
  writable,
}: {
  businessId: string;
  assessments: Assessment[];
  refresh: () => void;
  writable: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const active = useRef(true);
  const pending = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  async function synchronize(id: string) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setMessage("");
    try {
      const result = await workspaceRequest<Assessment>(
        `${assessmentsPath(businessId)}/${id}/sync`,
        jsonWrite("POST", {}),
      );
      if (active.current) {
        setMessage(
          result.processing_message ||
            (result.status === "completed_verified"
              ? "Salesforce completion verified."
              : "Completion not verified. Reconciliation never sends another invitation."),
        );
        refresh();
      }
    } catch (err) {
      if (active.current)
        setMessage(
          err instanceof Error ? err.message : "Synchronization unavailable.",
        );
    } finally {
      pending.current = false;
      if (active.current) setBusy(false);
    }
  }
  return (
    <>
      <p className="notice">
        Invitations are requested through the native Salesforce Lead Flow. No
        public survey link is used. A successful Lead creation does not confirm
        email delivery or assessment completion.
      </p>
      {writable && (
        <form
          className="workspace-form real-form"
          aria-busy={busy}
          onSubmit={async (event) => {
            event.preventDefault();
            if (pending.current) return;
            const form = new FormData(event.currentTarget);
            const recipient = {
              last_name: String(form.get("last_name")).trim(),
              email: String(form.get("email")).trim(),
            };
            if (!recipient.last_name) {
              setMessage("Enter the recipient’s actual last name.");
              return;
            }
            pending.current = true;
            setBusy(true);
            setMessage("");
            try {
              const record = await initiateAssessment(businessId);
              if (!active.current) return;
              const result = await workspaceRequest<Assessment>(
                `${assessmentsPath(businessId)}/${record.id}/dispatch`,
                jsonWrite("POST", recipient),
              );
              if (active.current) {
                setMessage(
                  result.dispatch_state === "sent"
                    ? "Lead created; Flow invitation requested. Email delivery is not verified."
                    : "Dispatch is pending or uncertain. Use reconciliation; do not create a second invitation.",
                );
                refresh();
                window.dispatchEvent(
                  new CustomEvent("kobentra-assessment-changed", {
                    detail: businessId,
                  }),
                );
              }
            } catch (err) {
              if (active.current)
                setMessage(
                  err instanceof Error ? err.message : "Dispatch unavailable.",
                );
            } finally {
              pending.current = false;
              if (active.current) setBusy(false);
            }
          }}
        >
          <label>
            Recipient last name
            <input name="last_name" required maxLength={80} disabled={busy} />
          </label>
          <label>
            Recipient email
            <input
              name="email"
              type="email"
              required
              maxLength={254}
              disabled={busy}
            />
          </label>
          <button className="button" disabled={busy}>
            {busy ? "Working…" : "Request assessment invitation"}
          </button>
          <p className="small-copy">
            Use an authorized business contact. The recipient is fixed once
            dispatch starts.
          </p>
        </form>
      )}
      {message && <p role="status">{message}</p>}
      {writable &&
        assessments
          .filter(
            (a) =>
              a.integration_mode === "salesforce_flow" &&
              a.dispatch_state &&
              a.status !== "completed_verified",
          )
          .map((a) => (
            <p key={a.id}>
              Assessment {a.id} · {a.dispatch_state}{" "}
              <button
                className="secondary"
                disabled={busy}
                onClick={() => synchronize(a.id)}
              >
                Reconcile / check completion
              </button>
            </p>
          ))}
    </>
  );
}
