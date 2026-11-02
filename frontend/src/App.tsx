import { Cta } from "./components/Primitives";
import { Home, How, Audience, Platform } from "./features/public/Pages";
import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
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
    <>
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
          <Link className="signin" to="/signin">
            Sign in
          </Link>
          <Link className="button small desktop-cta" to="/signup">
            Get started
            <ArrowUpRight size={16} />
          </Link>
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
          <Route path="/signup" element={<Auth signup />} />
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
          <Cta>Start your next chapter</Cta>
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
    </>
  );
}
export default function App() {
  return <Layout />;
}
