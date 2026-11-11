import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { AdminDashboard } from "./Dashboard";
import { AdminDirectory } from "./Directory";
import { AdminBusinessDetail } from "./BusinessDetail";
import "./admin.css";

export function AdminPortal({
  loading,
  error,
  signedIn,
  allowed,
}: {
  loading: boolean;
  error: string;
  signedIn: boolean;
  allowed: boolean;
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
  if (!signedIn) return <Navigate to="/signin" replace />;
  if (!allowed)
    return (
      <section className="section">
        <h1>Administration access restricted</h1>
        <p>This portal requires platform-owner authorization.</p>
        <Link className="button" to="/account">
          Return to account
        </Link>
      </section>
    );
  return (
    <section className="admin-shell">
      <aside className="admin-sidebar">
        <span className="eyebrow">KOBENTRA CONTROL ROOM</span>
        <strong>Platform administration</strong>
        <nav aria-label="Administration navigation">
          <NavLink end to="/admin">
            Dashboard
          </NavLink>
          <NavLink to="/admin/users">Users</NavLink>
          <NavLink to="/admin/businesses">Businesses</NavLink>
        </nav>
        <Link to="/account">Return to account</Link>
        <p>
          Owner-authorized administration.
          <br />
          Business decisions require a reason and audit record.
        </p>
      </aside>
      <div className="admin-content">
        <Routes>
          <Route index element={<AdminDashboard />} />
          <Route
            path="users"
            element={<AdminDirectory key="users" kind="users" />}
          />
          <Route
            path="businesses"
            element={<AdminDirectory key="businesses" kind="businesses" />}
          />
          <Route
            path="businesses/:businessId"
            element={<AdminBusinessDetail />}
          />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </div>
    </section>
  );
}
