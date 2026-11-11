import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { BusinessApiError, listBusinesses } from "./api";
import { BusinessSummary } from "./BusinessSummary";
import type { Business } from "./types";

export function BusinessAccount({
  email,
  logout,
}: {
  email: string;
  logout: () => Promise<void>;
}) {
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const location = useLocation();
  useEffect(() => {
    let active = true;
    listBusinesses()
      .then((data) => {
        if (active) setBusinesses(data);
      })
      .catch((err) => {
        if (active)
          setError(
            err instanceof BusinessApiError
              ? err.message
              : "Unable to load your businesses.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [attempt]);
  return (
    <section className="section">
      <span className="eyebrow">YOUR KOBENTRA ACCOUNT</span>
      <h1>Welcome to Kobentra.</h1>
      <p>
        You are securely signed in as <strong>{email}</strong>.
      </p>
      {location.state?.businessRegistered && (
        <p role="status">Your business registration has been saved.</p>
      )}
      {loading ? (
        <p role="status">Loading your businesses…</p>
      ) : error ? (
        <div role="alert">
          <p>{error}</p>
          <button
            className="secondary"
            onClick={() => {
              setError("");
              setLoading(true);
              setAttempt((a) => a + 1);
            }}
          >
            Retry
          </button>
          <Link className="text-link" to="/signin">
            Sign in again
          </Link>
        </div>
      ) : (
        <>
          <h2 style={{ fontSize: "2rem" }}>Your businesses</h2>
          {!businesses.length && <p>You haven’t registered a business yet.</p>}
          {businesses.map((business) => (
            <BusinessSummary
              key={business.organization_id}
              business={business}
            />
          ))}
          <Link className="button" to="/business/onboarding">
            {businesses.length
              ? "Register another business"
              : "Register your business"}
          </Link>
        </>
      )}
      <p className="small-copy">
        <Link className="text-link" to="/onboarding">
          Explore the fictional demo
        </Link>{" "}
        · Demo information is separate from your registered businesses.
      </p>
      <button className="secondary" type="button" onClick={logout}>
        Sign out
      </button>
    </section>
  );
}
