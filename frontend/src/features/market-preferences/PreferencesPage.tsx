import { useRef, useState } from "react";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import {
  preferencesPath,
  savePreferences,
  type Preference,
  type Preferences,
} from "./api";

export function PreferencesPage({
  businessId,
  writable,
}: {
  businessId: string;
  writable: boolean;
}) {
  const resource = useResource<Preferences>(preferencesPath(businessId));
  return (
    <>
      <h2>Market preferences</h2>
      <p>
        Define target countries and desired partner types. Sector and broader
        objective fields are not available yet.
      </p>
      {resource.data ? (
        <PreferencesForm
          key={businessId}
          businessId={businessId}
          writable={writable}
          initial={resource.data.preferences}
        />
      ) : (
        <ResourceState error={resource.error} retry={resource.retry} />
      )}
    </>
  );
}
function PreferencesForm({
  businessId,
  writable,
  initial,
}: {
  businessId: string;
  writable: boolean;
  initial: Preference[];
}) {
  const [rows, setRows] = useState(initial);
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  function update(index: number, field: keyof Preference, value: string) {
    setRows(
      rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
    );
    setMessage("");
  }
  return (
    <form
      className="workspace-form real-form"
      aria-busy={busy}
      onSubmit={async (event) => {
        event.preventDefault();
        if (pending.current || !writable) return;
        const values = rows.map((row) => ({
          country: row.country.trim(),
          partner_type: row.partner_type.trim(),
        }));
        if (values.some((row) => !row.country || !row.partner_type)) {
          setError("Enter a country and partner type for every row.");
          return;
        }
        if (
          new Set(
            values.map((row) =>
              JSON.stringify([
                row.country.toLowerCase(),
                row.partner_type.toLowerCase(),
              ]),
            ),
          ).size !== values.length
        ) {
          setError("Remove duplicate country/partner pairs.");
          return;
        }
        pending.current = true;
        setBusy(true);
        setError("");
        setMessage("");
        try {
          const saved = await savePreferences(businessId, values);
          setRows(saved.preferences);
          setMessage("Market preferences saved.");
        } catch (err) {
          setError(
            err instanceof Error ? err.message : "Unable to save preferences.",
          );
        } finally {
          pending.current = false;
          setBusy(false);
        }
      }}
    >
      {!rows.length && (
        <p>
          No target markets saved yet. Add a country and partner type to begin.
        </p>
      )}
      {rows.map((row, i) => (
        <fieldset
          className="preference-row"
          key={i}
          disabled={!writable || busy}
        >
          <legend>Target market {i + 1}</legend>
          <label>
            Country {i + 1}
            <input
              value={row.country}
              maxLength={80}
              required
              onChange={(e) => update(i, "country", e.target.value)}
            />
          </label>
          <label>
            Partner type {i + 1}
            <input
              value={row.partner_type}
              maxLength={40}
              required
              placeholder="e.g. Distributor, supplier or buyer"
              onChange={(e) => update(i, "partner_type", e.target.value)}
            />
          </label>
          {writable && (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setRows(rows.filter((_, index) => i !== index));
                setMessage("");
              }}
            >
              Remove target {i + 1}
            </button>
          )}
        </fieldset>
      ))}
      {writable && (
        <>
          <button
            className="secondary"
            type="button"
            disabled={busy || rows.length >= 50}
            onClick={() => {
              setRows([...rows, { country: "", partner_type: "" }]);
              setMessage("");
            }}
          >
            Add target market
          </button>
          <button className="button" disabled={busy}>
            {busy ? "Saving…" : "Save preferences"}
          </button>
        </>
      )}
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
