import { useState } from "react";
import type { BusinessDetail } from "./types";
import type { AdminAction } from "./management-types";
import { DecisionDialog } from "./DecisionDialog";
import { DecisionHistory } from "./DecisionHistory";
import { StatusBadges } from "./StatusBadges";

export function BusinessManagement({
  business,
  refresh,
  disabled: controlsDisabled = false,
}: {
  business: BusinessDetail;
  refresh: () => void;
  disabled?: boolean;
}) {
  const [action, setAction] = useState<AdminAction | null>(null);
  const state = business.administration;
  if (!state || !business.profile) return null;
  const controls: [AdminAction, string, boolean][] = [
    ["approve", "Approve", state.approval === "approved"],
    ["reject", "Reject", state.approval === "rejected"],
    ["verify_identity", "Verify identity", state.identity === "verified"],
    ["revoke_identity", "Revoke verification", state.identity === "unverified"],
    ["suspend", "Suspend", state.access === "suspended"],
    ["reactivate", "Reactivate", state.access === "active"],
    ["edit_profile", "Edit business", false],
  ];
  return (
    <>
      <section className="admin-panel">
        <h2>Business administration</h2>
        <StatusBadges value={state} />
        <p>
          Approval, independent identity verification and operational access are
          separate decisions. Publication approval and introduction safeguards
          still apply.
        </p>
        <div className="admin-management-actions">
          {controls.map(([key, label, disabled]) => (
            <button
              type="button"
              className="secondary"
              key={key}
              disabled={disabled || controlsDisabled}
              onClick={() => {
                setAction(key);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </section>
      {action && !controlsDisabled && (
        <DecisionDialog
          action={action}
          businessId={business.id}
          version={state.version}
          profile={business.profile}
          close={() => setAction(null)}
          saved={() => {
            setAction(null);
            refresh();
          }}
        />
      )}
      <DecisionHistory key={state.version} businessId={business.id} />
    </>
  );
}
