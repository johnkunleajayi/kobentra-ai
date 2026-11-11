import { useEffect, useRef, useState } from "react";
import type { Opportunity, OpportunityInput, Stage } from "./api";

export function OpportunityForm({
  initial,
  save,
  onSaved,
}: {
  initial?: OpportunityInput;
  save: (input: OpportunityInput) => Promise<Opportunity>;
  onSaved: (result: Opportunity) => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [stage, setStage] = useState<Stage>(initial?.stage ?? "exploring");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  return (
    <form
      className="workspace-form real-form"
      aria-busy={busy}
      onSubmit={async (event) => {
        event.preventDefault();
        if (pending.current) return;
        if (!title.trim()) {
          setError("Enter a title with visible characters.");
          return;
        }
        pending.current = true;
        setBusy(true);
        setError("");
        try {
          const result = await save({ title: title.trim(), stage });
          if (active.current) onSaved(result);
        } catch (err) {
          setError(
            err instanceof Error ? err.message : "Unable to save opportunity.",
          );
        } finally {
          pending.current = false;
          setBusy(false);
        }
      }}
    >
      <label>
        Opportunity title
        <input
          value={title}
          required
          maxLength={160}
          disabled={busy}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label>
        Status
        <select
          value={stage}
          disabled={busy}
          onChange={(e) => setStage(e.target.value as Stage)}
        >
          <option value="exploring">Exploring</option>
          <option value="conversation">In conversation</option>
          <option value="closed">Closed</option>
        </select>
      </label>
      <button className="button" disabled={busy}>
        {busy ? "Saving…" : initial ? "Save opportunity" : "Create opportunity"}
      </button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
