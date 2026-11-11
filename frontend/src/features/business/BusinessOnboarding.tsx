import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BusinessApiError, registerBusiness } from "./api";
import type { BusinessInput } from "./types";

export function BusinessOnboarding() {
  const navigate = useNavigate();
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <section className="section">
      <span className="eyebrow">YOUR KOBENTRA BUSINESS</span>
      <h1>Register your business.</h1>
      <p>
        Create a business profile linked to your signed-in account. This is
        separate from the fictional demo.
      </p>
      <form
        className="workspace-form"
        aria-busy={busy}
        onSubmit={async (event) => {
          event.preventDefault();
          if (pending.current) return;
          const data = new FormData(event.currentTarget);
          const input = Object.fromEntries(
            ["name", "sector", "country", "goal"].map((key) => [
              key,
              String(data.get(key) ?? "").trim(),
            ]),
          ) as unknown as BusinessInput;
          if (Object.values(input).some((value) => !value)) {
            setError("Enter a value with visible characters in every field.");
            return;
          }
          pending.current = true;
          setBusy(true);
          setError("");
          try {
            await registerBusiness(input);
            navigate("/account", {
              replace: true,
              state: { businessRegistered: true },
            });
          } catch (err) {
            setError(
              err instanceof BusinessApiError
                ? err.message
                : "Unable to save. Check your connection and retry; identical submissions are safe to retry.",
            );
          } finally {
            pending.current = false;
            setBusy(false);
          }
        }}
      >
        <label>
          Business name
          <input
            name="name"
            required
            maxLength={100}
            autoComplete="organization"
            disabled={busy}
          />
        </label>
        <label>
          Business sector
          <input
            name="sector"
            required
            maxLength={100}
            placeholder="e.g. Food & agriculture"
            disabled={busy}
          />
        </label>
        <label>
          Primary country or market
          <input
            name="country"
            required
            maxLength={80}
            placeholder="e.g. Ghana"
            disabled={busy}
          />
        </label>
        <label>
          Business goal
          <textarea name="goal" required maxLength={500} disabled={busy} />
        </label>
        {error && (
          <p role="alert">
            {error}{" "}
            <Link className="inline-link" to="/signin">
              Sign in again
            </Link>
          </p>
        )}
        <button className="button" disabled={busy}>
          {busy ? "Saving business…" : "Register business"}
        </button>
        <Link className="text-link" to="/account">
          Back to account
        </Link>
      </form>
    </section>
  );
}
