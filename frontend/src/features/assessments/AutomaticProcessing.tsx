import { useEffect, useState } from "react";
import { assessmentsPath, type Assessment } from "./api";
import { jsonWrite, workspaceRequest } from "../workspace/api";

export function AutomaticProcessing({
  businessId,
  writable,
}: {
  businessId: string;
  writable: boolean;
}) {
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!writable) return;
    let active = true,
      running = false,
      attempts = 0,
      nativeSeen = false;
    let timer: ReturnType<typeof setTimeout>;
    const ready = new Set<string>(),
      review = new Set<string>();
    async function tick() {
      if (!active || running || attempts >= 40) return;
      if (document.hidden) {
        timer = setTimeout(tick, 8000);
        return;
      }
      running = true;
      attempts++;
      try {
        const history = await workspaceRequest<{ assessments: Assessment[] }>(
          assessmentsPath(businessId),
        );
        const records = history.assessments
          .filter(
            (a) =>
              a.integration_mode === "salesforce_flow" &&
              (a.dispatch_state || a.status === "completed_verified"),
          )
          .sort((a, b) => b.initiated_at.localeCompare(a.initiated_at))
          .slice(0, 3);
        nativeSeen = records.length > 0;
        for (const assessment of records) {
          if (!active || ready.has(assessment.id) || review.has(assessment.id))
            continue;
          setMessage("Processing your assessment.");
          const result = await workspaceRequest<Assessment>(
            `${assessmentsPath(businessId)}/${assessment.id}/sync`,
            jsonWrite("POST", {}),
          );
          if (!active) return;
          setMessage(
            result.processing_message || "Waiting for assessment completion.",
          );
          if (result.processing_status === "ready") {
            ready.add(assessment.id);
            window.dispatchEvent(
              new CustomEvent("kobentra-assessment-processed", {
                detail: businessId,
              }),
            );
          } else if (result.processing_status === "needs_review")
            review.add(assessment.id);
        }
      } catch {
        if (active && nativeSeen)
          setMessage(
            "Assessment processing is temporarily unavailable. It will retry safely.",
          );
      } finally {
        running = false;
        if (active && attempts < 40) timer = setTimeout(tick, 8000);
        else if (active && nativeSeen && !ready.size)
          setMessage(
            "Automatic checks paused. Retry processing when your assessment is submitted.",
          );
      }
    }
    function wake(event: Event) {
      if ((event as CustomEvent).detail !== businessId) return;
      clearTimeout(timer);
      attempts = 0;
      review.clear();
      void tick();
    }
    window.addEventListener("kobentra-assessment-changed", wake);
    void tick();
    return () => {
      active = false;
      clearTimeout(timer);
      window.removeEventListener("kobentra-assessment-changed", wake);
    };
  }, [businessId, writable]);
  if (!message) return null;
  return (
    <aside
      className="workspace-note"
      aria-label="Automatic assessment processing"
    >
      <p aria-live="polite">{message}</p>
      <button
        type="button"
        className="secondary"
        onClick={() =>
          window.dispatchEvent(
            new CustomEvent("kobentra-assessment-changed", {
              detail: businessId,
            }),
          )
        }
      >
        Retry processing
      </button>
    </aside>
  );
}
