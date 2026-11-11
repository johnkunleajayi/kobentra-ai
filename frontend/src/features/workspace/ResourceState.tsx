import { Link } from "react-router-dom";

export function ResourceState({
  error,
  retry,
}: {
  error?: string;
  retry: () => void;
}) {
  return error ? (
    <div role="alert">
      <p>{error}</p>
      <button className="secondary" onClick={retry}>
        Retry
      </button>{" "}
      <Link to="/account">Return to account</Link>
    </div>
  ) : (
    <p role="status">Loading workspace data…</p>
  );
}
