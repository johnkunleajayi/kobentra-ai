import { Cta } from "./components/Primitives";
import { AuthenticatedPage } from "./features/auth/AuthenticatedPage";
import { BusinessAccount } from "./features/business/BusinessAccount";
import { BusinessOnboarding } from "./features/business/BusinessOnboarding";
import { BusinessSelection } from "./features/workspace/BusinessSelection";
import { BusinessWorkspace } from "./features/workspace/BusinessWorkspace";
import { AuthContext } from "./features/auth/AuthContext";
import {
  getCurrentUser,
  signOut,
  type AuthenticatedUser,
} from "./features/auth/session";
import { Home, How, Audience, Platform } from "./features/public/Pages";
import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation, Navigate } from "react-router-dom";
import { ArrowUpRight, Sun, Moon, Menu, X } from "lucide-react";
import { Auth } from "./features/auth/Auth";
import { Workspace } from "./features/demo/Workspace";
const A = "/assets/";
const pages = [
  ["/how-it-works", "How it works"],
  ["/businesses", "For businesses"],
  ["/organizers", "For event organizers"],
  ["/platform", "Platform"],
];
function Layout() {
  const [dark, setDark] = useState(
    () => localStorage.getItem("kobentra-theme") === "dark",
  );
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((result) => {
        if (active) setUser(result);
      })
      .catch(() => {
        if (active) setAuthError("Session check unavailable.");
      })
      .finally(() => {
        if (active) setAuthLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function logout() {
    try {
      await signOut();
      setUser(null);
      window.location.assign("/signin");
    } catch {
      setAuthError("Sign-out failed. Please try again.");
    }
  }
  const { pathname } = useLocation();
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("kobentra-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    window.scrollTo(0, 0);
    document.title = `Kobentra — ${pathname === "/" ? "Connections that move business forward" : pathname.split("/").filter(Boolean).join(" / ")}`;
  }, [pathname]);
  return (
    <AuthContext.Provider value={Boolean(user)}>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="header">
        <Link to="/" aria-label="Kobentra home" onClick={() => setOpen(false)}>
          <img
            className="logo"
            src={`${A}brand/kobentra-logo-${dark ? "dark" : "light"}.png`}
            alt="Kobentra"
            width="181"
            height="60"
          />
        </Link>
        <nav className={open ? "nav open" : "nav"} aria-label="Main navigation">
          {pages.map(([to, label]) => (
            <NavLink onClick={() => setOpen(false)} key={to} to={to}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="header-actions">
          <button
            className="icon-button theme"
            aria-label={dark ? "Use light theme" : "Use dark theme"}
            onClick={() => setDark(!dark)}
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          {user ? (
            <>
              <Link className="signin" to="/account">
                My account
              </Link>
              <button className="signin" type="button" onClick={logout}>
                Sign out
              </button>
            </>
          ) : (
            <Link className="signin" to="/signin">
              Sign in
            </Link>
          )}
          {!user && (
            <Link className="button small desktop-cta" to="/signup">
              Get started
              <ArrowUpRight size={16} />
            </Link>
          )}
          <button
            className="icon-button menu"
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            {open ? <X /> : <Menu />}
          </button>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/how-it-works" element={<How />} />
          <Route path="/businesses" element={<Audience />} />
          <Route path="/organizers" element={<Audience organizer />} />
          <Route path="/platform" element={<Platform />} />
          <Route path="/signin" element={<Auth />} />
          <Route path="/workspace" element={<AuthenticatedPage loading={authLoading} error={authError} signedIn={Boolean(user)}><BusinessSelection /></AuthenticatedPage>} />
          <Route path="/workspace/:businessId/*" element={<AuthenticatedPage loading={authLoading} error={authError} signedIn={Boolean(user)}><BusinessWorkspace /></AuthenticatedPage>} />
          <Route path="/business/onboarding" element={
            <AuthenticatedPage loading={authLoading} error={authError} signedIn={Boolean(user)}>
              <BusinessOnboarding />
            </AuthenticatedPage>
          } />
          <Route
            path="/account"
            element={
              authLoading ? (
                <section className="section" aria-live="polite">
                  Checking your session...
                </section>
              ) : authError ? (
                <section className="section" role="alert">
                  <h1>Session unavailable</h1>
                  <p>{authError}</p>
                  <button className="button" onClick={() => window.location.reload()}>
                    Retry
                  </button>
                </section>
              ) : user ? (
                <BusinessAccount email={user.email} logout={logout} />
              ) : (
                <Navigate to="/signin" replace />
              )
            }
          />
          <Route path="/signup" element={user ? <Navigate to="/account" replace /> : <Auth signup />} />
          <Route path="/onboarding" element={<Auth onboarding />} />
          <Route path="/demo/*" element={<Workspace />} />
          <Route
            path="*"
            element={
              <section className="section">
                <h1>Let’s find your way.</h1>
                <p>This page isn’t here. Your next connection could be.</p>
                <Cta to="/">Back to home</Cta>
              </section>
            }
          />
        </Routes>
      </main>
      <footer>
        <div className="footer-top">
          <Link to="/">
            <img
              className="logo"
              src={`${A}brand/kobentra-logo-dark.png`}
              alt="Kobentra"
              width="181"
              height="60"
            />
          </Link>
          <p>
            Built for the ambition.
            <br />
            Connected by possibility.
          </p>
          {!user && <Cta>Start your next chapter</Cta>}
        </div>
        <div className="footer-bottom">
          <span>
            © {new Date().getFullYear()} Kobentra AI · Phase 1 preview
          </span>
          <div>
            <Link to="/platform">Trust & architecture</Link>
            <Link to="/demo">Explore local demo ↗</Link>
          </div>
          <span>Made for West Africa. Open to possibility.</span>
        </div>
      </footer>
    </AuthContext.Provider>
  );
}
export default function App() {
  return <Layout />;
}
