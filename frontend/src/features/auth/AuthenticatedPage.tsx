import type { ReactNode } from "react";
import { startGoogleLogin } from "./session";

export function AuthenticatedPage({
  loading,
  error,
  signedIn,
  children,
}: {
  loading: boolean;
  error: string;
  signedIn: boolean;
  children: ReactNode;
}) {
  if (loading)
    return (
      <section className="section" role="status">
        Checking your session…
      </section>
    );
  if (error)
    return (
      <section className="section" role="alert">
        <h1>Session unavailable</h1>
        <p>{error}</p>
        <button className="button" onClick={() => window.location.reload()}>
          Retry
        </button>
      </section>
    );
  if (!signedIn)
    return (
      <section className="section">
        <h1>Sign in to register your business.</h1>
        <p>
          Your business will be linked to your authenticated Kobentra account.
        </p>
        <button className="button" onClick={startGoogleLogin}>
          Continue with Google
        </button>
      </section>
    );
  return children;
}
