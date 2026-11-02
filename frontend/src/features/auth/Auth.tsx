import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowUpRight, LockKeyhole } from "lucide-react";
import { emailProvider } from "../contracts";
export function Auth({
  signup = false,
  onboarding = false,
}: {
  signup?: boolean;
  onboarding?: boolean;
}) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  return (
    <section className="auth section">
      <div className="auth-aside">
        <span className="eyebrow">YOUR AMBITION BELONGS HERE</span>
        <h1>
          Good business
          <br />
          starts with
          <br />a <em>connection.</em>
        </h1>
        <p>
          A wider network. A more focused search.
          <br />A new possibility for your business.
        </p>
        <LockKeyhole />
        <p className="small-copy">
          Phase 1 preview · Authentication not connected.
          <br />
          Never enter a real password or private business details.
        </p>
      </div>
      <div className="auth-panel">
        <span className="eyebrow">
          {onboarding
            ? "LOCAL DEMO SETUP"
            : signup
              ? "LET’S GET ACQUAINTED"
              : "WELCOME TO KOBENTRA"}
        </span>
        <h2>
          {onboarding
            ? "Shape your demo."
            : signup
              ? "Start your next chapter."
              : "Welcome back."}
        </h2>
        <p>
          {onboarding
            ? "Use fictional details only. This profile lives in your browser session."
            : "Email and Google authentication are planned. Forms validate locally; no real account or login session is created."}
        </p>
        {!onboarding && (
          <>
            <button
              className="provider-button"
              onClick={() =>
                setMessage(
                  "Google sign-in is not configured. No authentication was started.",
                )
              }
            >
              <span aria-hidden="true">G</span> Continue with Google{" "}
              <span className="badge">Not configured</span>
            </button>
            <div className="divider">or explore the email form</div>
          </>
        )}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setMessage("");
            const form = e.currentTarget;
            const data = new FormData(form);
            if (onboarding) {
              const profile = {
                name: String(data.get("name")).trim(),
                sector: String(data.get("sector")),
                country: String(data.get("country")),
                goal: String(data.get("goal")).trim(),
              };
              if (!profile.name || !profile.goal) {
                setMessage(
                  "Enter a business name and goal with visible characters.",
                );
                return;
              }
              sessionStorage.setItem(
                "kobentra-demo-profile",
                JSON.stringify(profile),
              );
              navigate("/demo");
              return;
            }
            setBusy(true);
            try {
              await emailProvider.signIn(
                String(data.get("email")),
                String(data.get("password")),
              );
            } catch (err) {
              setMessage(
                err instanceof Error
                  ? err.message
                  : "Authentication is unavailable.",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          {onboarding ? (
            <>
              <label>
                Fictional business name
                <input
                  name="name"
                  required
                  maxLength={100}
                  placeholder="e.g. Sample Harvest Co."
                />
              </label>
              <label>
                Sector
                <select name="sector">
                  <option>Food & agriculture</option>
                  <option>Manufacturing</option>
                  <option>Retail & trade</option>
                  <option>Technology</option>
                </select>
              </label>
              <label>
                Primary market
                <select name="country">
                  <option>Nigeria</option>
                  <option>Ghana</option>
                  <option>Senegal</option>
                  <option>Côte d’Ivoire</option>
                </select>
              </label>
              <label>
                Your business goal
                <textarea
                  name="goal"
                  required
                  maxLength={500}
                  placeholder="e.g. Explore distribution partnerships"
                />
              </label>
            </>
          ) : (
            <>
              {signup && (
                <label>
                  Your name (sample only)
                  <input
                    name="name"
                    autoComplete="off"
                    required
                    maxLength={100}
                  />
                </label>
              )}
              <label>
                Email address
                <input
                  type="email"
                  name="email"
                  autoComplete="off"
                  placeholder="you@example.com"
                  required
                  maxLength={254}
                />
              </label>
              <label>
                Password (sample only)
                <input
                  type="password"
                  name="password"
                  autoComplete="off"
                  required
                  minLength={12}
                  maxLength={128}
                  aria-describedby="password-help"
                />
              </label>
              <p id="password-help" className="small-copy">
                At least 12 characters. Use a dummy password for this preview.
              </p>
              {signup && (
                <label className="checkbox">
                  <input type="checkbox" required /> I understand this is a
                  local preview and no account will be created.
                </label>
              )}
            </>
          )}
          <button className="button" disabled={busy} type="submit">
            {onboarding
              ? "Enter local demo"
              : signup
                ? "Validate sign-up form"
                : "Validate sign-in form"}
            <ArrowUpRight size={18} />
          </button>
        </form>
        <p role="status" className="form-status">
          {message}
        </p>
        {!onboarding && (
          <>
            <p>
              {signup ? "Already exploring?" : "New to Kobentra?"}{" "}
              <Link className="inline-link" to={signup ? "/signin" : "/signup"}>
                {signup ? "Sign in" : "Sign up"}
              </Link>
            </p>
            <Link className="demo-entry" to="/onboarding">
              Explore a clearly labeled local demo <ArrowUpRight size={17} />
            </Link>
          </>
        )}
        <p className="small-copy">
          Salesforce and EventSpark are not connected.
        </p>
      </div>
    </section>
  );
}
