import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  ArrowUpRight,
  LayoutDashboard,
  Building2,
  Compass,
  Handshake,
  BriefcaseBusiness,
  CalendarDays,
  Settings,
  X,
  Search,
} from "lucide-react";
import { filterMatches } from "./data";
import type {
  BusinessProfile,
  Introduction,
  Match,
  Opportunity,
} from "../contracts";
const nav = [
  ["", "Overview", LayoutDashboard],
  ["profile", "Business Profile", Building2],
  ["discover", "Discover", Compass],
  ["introductions", "Introductions", Handshake],
  ["opportunities", "Opportunities", BriefcaseBusiness],
  ["events", "Events", CalendarDays],
  ["settings", "Settings", Settings],
] as const;
const initialProfile = {
  name: "Sample Harvest Co.",
  sector: "Food & agriculture",
  country: "Nigeria",
  goal: "Explore distribution partnerships in West Africa.",
};
function readProfile(): BusinessProfile {
  try {
    const p = JSON.parse(
      sessionStorage.getItem("kobentra-demo-profile") || "null",
    );
    return p &&
      typeof p.name === "string" &&
      typeof p.goal === "string" &&
      typeof p.country === "string" &&
      typeof p.sector === "string"
      ? p
      : initialProfile;
  } catch {
    return initialProfile;
  }
}
export function Workspace() {
  const slug = useLocation().pathname.split("/")[2] || "";
  const [profile, setProfile] = useState<BusinessProfile>(readProfile);
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("All markets");
  const [selected, setSelected] = useState<Match | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (!selected || !dialogRef.current) return;
    const previousFocus = document.activeElement;
    dialogRef.current.showModal();
    return () => {
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, [selected]);
  const [introductions, setIntroductions] = useState<Introduction[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [status, setStatus] = useState("");
  const [eventSaved, setEventSaved] = useState(false);
  const title = nav.find((n) => n[0] === slug)?.[1] || "Workspace";
  function saveOpportunity(m: Match) {
    if (opportunities.some((o) => o.id === m.id)) {
      setStatus("Already saved to your demo pipeline.");
      return;
    }
    setOpportunities([
      ...opportunities,
      { id: m.id, name: m.name, stage: "Exploring" },
    ]);
    setStatus("Saved to your local demo pipeline.");
  }
  return (
    <div className="workspace-wrap">
      <div className="demo-banner">
        <span>
          <strong>LOCAL DEMO</strong> · Fictional businesses and events. Actions
          simulate local state only; nothing is sent.
        </span>
        <Link to="/">
          Exit demo <ArrowUpRight size={15} />
        </Link>
      </div>
      <div className="workspace">
        <aside className="sidebar">
          <div className="org-avatar">SH</div>
          <strong>{profile.name}</strong>
          <span>Demo organization</span>
          <nav aria-label="Workspace navigation">
            {nav.map(([path, label, Icon]) => (
              <NavLink end to={"/demo" + (path ? "/" + path : "")} key={path}>
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="connection-state">
            <span className="tiny-dot" />
            Integrations disconnected
          </div>
        </aside>
        <section className="workspace-content">
          <div className="workspace-heading">
            <div>
              <span className="eyebrow">YOUR BUSINESS, IN MOTION</span>
              <h1>{title}</h1>
            </div>
            <span className="badge">Demo workspace</span>
          </div>
          <p className="form-status" role="status">
            {status}
          </p>
          {slug === "" && (
            <>
              <div className="welcome-card">
                <div>
                  <span className="eyebrow">THE NEXT CHAPTER IS YOURS</span>
                  <h2>
                    Let’s find your
                    <br />
                    next connection.
                  </h2>
                  <p>{profile.goal}</p>
                  <Link className="button" to="/demo/discover">
                    Explore sample matches <ArrowUpRight size={18} />
                  </Link>
                </div>
                <Compass size={150} strokeWidth={0.7} />
              </div>
              <div className="stat-grid">
                {[
                  ["Sample matches", "3"],
                  [
                    "Local introduction requests",
                    String(
                      introductions.filter((i) => i.status === "requested")
                        .length,
                    ),
                  ],
                  ["Saved opportunities", String(opportunities.length)],
                ].map(([label, value]) => (
                  <div key={label}>
                    <strong>{value}</strong>
                    <span>{label}</span>
                  </div>
                ))}
              </div>
              <div className="workspace-note">
                <h3>A considered start.</h3>
                <p>
                  Your demonstration profile focuses on{" "}
                  {profile.sector.toLowerCase()} in {profile.country}. Review
                  sample match explanations, simulate a request and organize a
                  local pipeline. Requests and opportunities reset when the page
                  reloads; no real contact details are available.
                </p>
                <Link className="text-link" to="/demo/profile">
                  Review your profile <ArrowUpRight size={16} />
                </Link>
              </div>
            </>
          )}
          {slug === "profile" && (
            <form
              className="workspace-form"
              onSubmit={(e) => {
                e.preventDefault();
                const d = new FormData(e.currentTarget);
                const next = {
                  name: String(d.get("name")).trim(),
                  sector: String(d.get("sector")),
                  country: String(d.get("country")),
                  goal: String(d.get("goal")).trim(),
                };
                if (!next.name || !next.goal) {
                  setStatus("Enter a name and goal with visible characters.");
                  return;
                }
                setProfile(next);
                sessionStorage.setItem(
                  "kobentra-demo-profile",
                  JSON.stringify(next),
                );
                setStatus("Fictional profile saved in this browser session.");
              }}
            >
              <p>Fictional details only. No data is sent to an API.</p>
              <label>
                Business name
                <input
                  name="name"
                  defaultValue={profile.name}
                  maxLength={100}
                  required
                />
              </label>
              <label>
                Sector
                <select name="sector" defaultValue={profile.sector}>
                  <option>Food & agriculture</option>
                  <option>Manufacturing</option>
                  <option>Retail & trade</option>
                  <option>Technology</option>
                </select>
              </label>
              <label>
                Market
                <select name="country" defaultValue={profile.country}>
                  <option>Nigeria</option>
                  <option>Ghana</option>
                  <option>Senegal</option>
                  <option>Côte d’Ivoire</option>
                </select>
              </label>
              <label>
                Goal
                <textarea
                  name="goal"
                  defaultValue={profile.goal}
                  maxLength={500}
                  required
                />
              </label>
              <button className="button">Save demo profile</button>
            </form>
          )}
          {slug === "discover" && (
            <>
              <p>
                Every result is fictional. Explanations illustrate potential fit
                and are not generated by a live AI service.
              </p>
              <div className="discovery-filters">
                <label>
                  <span>Search sample businesses</span>
                  <div className="search-input">
                    <Search size={18} />
                    <input
                      type="search"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Try distributor or packaging"
                    />
                  </div>
                </label>
                <label>
                  Market
                  <select
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                  >
                    {["All markets", "Ghana", "Nigeria", "Senegal"].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="matches">
                {filterMatches(query, country).map((m) => (
                  <article key={m.id}>
                    <div className="match-top">
                      <span className="org-avatar">{m.initials}</span>
                      <span className="badge">Sample · {m.kind}</span>
                    </div>
                    <h3>{m.name}</h3>
                    <p>
                      {m.country} · {m.sector}
                    </p>
                    <details>
                      <summary>Why this sample match?</summary>
                      <p>{m.explanation}</p>
                    </details>
                    <div className="match-actions">
                      <button
                        className="button small"
                        onClick={() => setSelected(m)}
                      >
                        Simulate introduction
                      </button>
                      <button
                        className="secondary small"
                        onClick={() => saveOpportunity(m)}
                      >
                        Save opportunity
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              {!filterMatches(query, country).length && (
                <p className="empty">
                  No sample matches fit these filters. Try another market or
                  search.
                </p>
              )}
            </>
          )}
          {slug === "introductions" && (
            <>
              <p>
                A request does not grant access to contact details. Real
                introductions will require both sides to consent.
              </p>
              {introductions.length ? (
                introductions.map((i) => (
                  <article className="record" key={i.id}>
                    <div>
                      <h3>{i.name}</h3>
                      <p>{i.message}</p>
                      <span className="badge">
                        Local simulation · {i.status}
                      </span>
                    </div>
                    {i.status === "requested" && (
                      <button
                        className="secondary"
                        onClick={() => {
                          setIntroductions(
                            introductions.map((item) =>
                              item.id === i.id
                                ? { ...item, status: "withdrawn" }
                                : item,
                            ),
                          );
                          setStatus("Local request withdrawn.");
                        }}
                      >
                        Withdraw request
                      </button>
                    )}
                  </article>
                ))
              ) : (
                <div className="empty">
                  <Handshake size={35} />
                  <h3>A conversation starts here.</h3>
                  <p>You haven’t simulated an introduction yet.</p>
                  <Link className="button" to="/demo/discover">
                    Explore samples
                  </Link>
                </div>
              )}
            </>
          )}
          {slug === "opportunities" && (
            <>
              <p>
                Organize fictional prospects. This pipeline is in memory and
                resets on reload.
              </p>
              {opportunities.length ? (
                opportunities.map((o) => (
                  <article className="record" key={o.id}>
                    <h3>{o.name}</h3>
                    <label>
                      Stage
                      <select
                        value={o.stage}
                        onChange={(e) =>
                          setOpportunities(
                            opportunities.map((item) =>
                              item.id === o.id
                                ? {
                                    ...item,
                                    stage: e.target
                                      .value as Opportunity["stage"],
                                  }
                                : item,
                            ),
                          )
                        }
                      >
                        {["Exploring", "In conversation", "Closed"].map((s) => (
                          <option key={s}>{s}</option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="secondary"
                      onClick={() => {
                        setOpportunities(
                          opportunities.filter((item) => item.id !== o.id),
                        );
                        setStatus("Removed from your demo pipeline.");
                      }}
                    >
                      Remove
                    </button>
                  </article>
                ))
              ) : (
                <div className="empty">
                  <BriefcaseBusiness size={35} />
                  <h3>Room for your next opportunity.</h3>
                  <p>Save a sample match to begin your local pipeline.</p>
                  <Link className="button" to="/demo/discover">
                    Discover samples
                  </Link>
                </div>
              )}
            </>
          )}
          {slug === "events" && (
            <>
              <div className="notice">
                Fictional event demonstration. No live events or
                registrations are available.
              </div>
              <article className="event-card">
                <span className="eyebrow">FICTIONAL SAMPLE EVENT</span>
                <h2>Coastal Business Exchange</h2>
                <p>Illustrative trade networking event · Accra, Ghana</p>
                <p>
                  No date, venue, registration or attendance is confirmed. This
                  card demonstrates discovery only.
                </p>
                <button
                  className="button"
                  onClick={() => {
                    setEventSaved(!eventSaved);
                    setStatus(
                      eventSaved
                        ? "Sample event unsaved."
                        : "Sample event saved locally. No registration was made.",
                    );
                  }}
                >
                  {eventSaved ? "Unsave sample event" : "Save sample event"}
                </button>
              </article>
            </>
          )}
          {slug === "settings" && (
            <>
              <div className="workspace-note">
                <h3>Local demo controls</h3>
                <p>
                  Theme controls are in the main header. The fictional profile
                  is saved to session storage; all other sample interactions
                  stay in memory.
                </p>
                <button
                  className="secondary"
                  onClick={() => {
                    sessionStorage.removeItem("kobentra-demo-profile");
                    setProfile(initialProfile);
                    setIntroductions([]);
                    setOpportunities([]);
                    setEventSaved(false);
                    setStatus("Local demo data reset.");
                  }}
                >
                  Reset local demo data
                </button>
              </div>
              <div className="workspace-note">
                <h3>Integration status</h3>
                <p>
                  This fictional workspace does not use live integrations.
                  <br />
                  Sign in with Google to manage your real business.
                  <br />
                  The real platform connects to Salesforce and SurveyVista.
                </p>
              </div>
            </>
          )}
          {!nav.some((n) => n[0] === slug) && (
            <div className="empty">
              <h2>This workspace page isn’t available.</h2>
              <Link to="/demo">Return to overview</Link>
            </div>
          )}
        </section>
      </div>
      {selected && (
        <div
          className="dialog-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSelected(null);
          }}
        >
          <dialog
            ref={dialogRef}
            onCancel={(event) => {
              event.preventDefault();
              setSelected(null);
            }}
            aria-modal="true"
            aria-labelledby="intro-title"
            onKeyDown={(e) => {
              if (e.key === "Escape") setSelected(null);
              if (e.key === "Tab") {
                const els = e.currentTarget.querySelectorAll<HTMLElement>(
                  "button,textarea,input",
                );
                const first = els[0],
                  last = els[els.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                  e.preventDefault();
                  last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                  e.preventDefault();
                  first.focus();
                }
              }
            }}
          >
            <button
              className="icon-button close"
              aria-label="Close introduction"
              onClick={() => setSelected(null)}
            >
              <X />
            </button>
            <span className="eyebrow">LOCAL SIMULATION</span>
            <h2 id="intro-title">Start a conversation.</h2>
            <p>
              To {selected.name}, a fictional business. Nothing is sent and no
              contact details will be released.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const msg = String(
                  new FormData(e.currentTarget).get("message"),
                ).trim();
                if (msg.length < 10) {
                  setStatus(
                    "Use at least 10 visible characters in your message.",
                  );
                  return;
                }
                setIntroductions([
                  ...introductions,
                  {
                    id: crypto.randomUUID(),
                    matchId: selected.id,
                    name: selected.name,
                    message: msg,
                    status: "requested",
                  },
                ]);
                setStatus(
                  "Introduction request simulated locally. No real message was sent.",
                );
                setSelected(null);
              }}
            >
              <label>
                Your sample message
                <textarea
                  name="message"
                  required
                  minLength={10}
                  maxLength={1000}
                  placeholder="Describe a fictional business opportunity…"
                />
              </label>
              <label className="checkbox">
                <input type="checkbox" required /> I understand this is a
                simulation, not a real introduction.
              </label>
              <button className="button">Save simulated request</button>
            </form>
          </dialog>
        </div>
      )}
    </div>
  );
}
