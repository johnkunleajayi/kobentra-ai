import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  ShieldCheck,
  MoveUpRight,
  Network,
  Globe2,
  ChevronDown,
} from "lucide-react";
import { Picture, Cta, Eyebrow } from "../../components/Primitives";
export function Home() {
  return (
    <>
      <section className="hero section">
        <div className="hero-copy">
          <Eyebrow>AFRICAN AMBITION. CONNECTED.</Eyebrow>
          <h1>
            Your next big
            <br />
            opportunity starts
            <br />
            with a <em>connection.</em>
          </h1>
          <div className="hero-bottom">
            <p>
              Meet the buyers, suppliers and partners who can move your business
              forward. Across West Africa. Beyond your network.
            </p>
            <div className="cta-row">
              <Cta />
              <Link className="text-link" to="/how-it-works">
                See how it works <ArrowRight size={17} />
              </Link>
            </div>
          </div>
          <div className="hero-caption">
            <span className="tiny-dot" />
            Built around your business. Driven by your ambition.
          </div>
        </div>
        <div className="hero-art">
          <Picture
            priority
            file="home/home-hero-business-connections.png"
            alt="African business professionals sharing a conversation at a networking event"
          />
          <div className="image-topline">
            <span>GOOD CONNECTIONS. NEW POSSIBILITIES.</span>
            <span>01 / 06</span>
          </div>
          <div className="hero-stamp">
            <Network size={28} />
            <span>
              Local knowledge.
              <br />
              <strong>Wider horizons.</strong>
            </span>
            <MoveUpRight size={26} />
          </div>
          <span className="image-note">Illustrative business imagery</span>
        </div>
      </section>
      <div className="market-strip">
        <span>ONE CONNECTED BUSINESS ECOSYSTEM</span>
        <p>
          Buyers <i>✳</i> Suppliers <i>✳</i> Distributors <i>✳</i> Investors{" "}
          <i>✳</i> Partners
        </p>
      </div>
      <section className="section possibility">
        <div className="section-heading">
          <div>
            <Eyebrow>THE RIGHT PEOPLE CHANGE EVERYTHING</Eyebrow>
            <h2>
              Big ambition.
              <br />
              <span className="muted">Meet real possibility.</span>
            </h2>
          </div>
          <p>
            A great product deserves the right market. A growing business
            deserves the right partner. Kobentra is being built to bring those
            worlds together.
          </p>
        </div>
        <div className="editorial-grid">
          <article className="feature-large">
            <Picture
              file="home/home-african-entrepreneur.png"
              alt="Food entrepreneur standing in her production facility"
            />
            <div className="feature-caption">
              <span>01 / BUILT FOR YOUR BUSINESS</span>
              <h3>
                You’ve built something.
                <br />
                Let’s help it go further.
              </h3>
              <Link
                className="circle-link"
                to="/businesses"
                aria-label="Explore Kobentra for businesses"
              >
                <ArrowUpRight />
              </Link>
            </div>
          </article>
          <div className="feature-stack">
            <article className="orange-card">
              <Globe2 size={35} />
              <h3>
                Your market doesn’t
                <br />
                end at the border.
              </h3>
              <p>
                Explore commercial connections shaped around your sector, goals
                and preferred markets.
              </p>
              <Link to="/platform">
                Discover the platform <ArrowUpRight size={20} />
              </Link>
            </article>
            <article className="mini-image-card">
              <Picture
                file="home/home-business-partnerships.png"
                alt="Entrepreneurs discussing a potential business partnership"
              />
              <div>
                <span>BETTER TOGETHER</span>
                <h3>
                  A handshake.
                  <br />A new chapter.
                </h3>
                <Link
                  to="/how-it-works"
                  aria-label="Learn about consent-based introductions"
                >
                  <ArrowUpRight />
                </Link>
              </div>
            </article>
          </div>
        </div>
      </section>
      <section className="how-preview section">
        <div>
          <Eyebrow>A CLEAR PATH FORWARD</Eyebrow>
          <h2>
            From “what if”
            <br />
            to <em>“let’s talk.”</em>
          </h2>
          <p>
            Turn your business goals into a focused search for your next
            commercial connection.
          </p>
          <Cta to="/how-it-works">How Kobentra works</Cta>
        </div>
        <ol className="steps-preview">
          {[
            "Tell us about your business",
            "Discover relevant matches",
            "Request an introduction",
            "Move opportunities forward",
          ].map((t, i) => (
            <li key={t}>
              <span>0{i + 1}</span>
              <h3>{t}</h3>
              <ArrowUpRight size={22} />
            </li>
          ))}
        </ol>
      </section>
      <section className="section">
        <div className="section-heading">
          <div>
            <Eyebrow>MORE WAYS TO MOVE FORWARD</Eyebrow>
            <h2>
              Find your next <em>opening.</em>
            </h2>
          </div>
          <Link className="text-link" to="/demo/discover">
            Explore the local demo <ArrowUpRight size={20} />
          </Link>
        </div>
        <div className="story-grid">
          {[
            [
              "home-business-growth.png",
              "GROWTH",
              "Think beyond your current market.",
              "/businesses",
            ],
            [
              "home-event-discovery.png",
              "EVENTS",
              "Be in the room that matters.",
              "/organizers",
            ],
            [
              "home-business-opportunity-notifications.png",
              "OPPORTUNITIES",
              "Give your next opportunity a home.",
              "/platform",
            ],
          ].map(([file, tag, title, to]) => (
            <Link className="story" to={to} key={file}>
              <Picture file={"home/" + file} alt={title} />
              <div>
                <span className="eyebrow">{tag}</span>
                <h3>{title}</h3>
                <ArrowUpRight />
              </div>
            </Link>
          ))}
        </div>
        <p className="art-disclaimer">
          Marketing images are illustrative. Embedded notifications, metrics and
          controls are artwork, not live product results.
        </p>
      </section>
      <section className="trust section">
        <ShieldCheck size={42} />
        <div>
          <Eyebrow>CONNECTION STARTS WITH CONSENT</Eyebrow>
          <h2>
            Your business.
            <br />
            Your connections. Your choice.
          </h2>
          <p>
            Introductions should open doors, not expose your details. The
            planned workflow requires both sides to agree before private contact
            details are shared.
          </p>
          <Link className="text-link" to="/platform">
            Explore our approach to trust <ArrowUpRight size={18} />
          </Link>
        </div>
        <div className="trust-mark">
          Together,
          <br />
          we go <em>further.</em>
          <span>✳</span>
        </div>
      </section>
      <section className="final-cta section">
        <Eyebrow>YOUR NEXT CHAPTER</Eyebrow>
        <h2>
          Opportunity is out there.
          <br />
          Let’s make the connection.
        </h2>
        <Cta>Get started with Kobentra</Cta>
        <p>Explore the preview. No Salesforce account required.</p>
      </section>
    </>
  );
}
const steps = [
  [
    "Sign up",
    "Your ambition is the starting point.",
    "Choose how you want to join. Email and Google entry methods are planned; the local preview never creates a real account.",
    "01-signup",
  ],
  [
    "Create your business profile",
    "Give opportunity a little context.",
    "Tell Kobentra what you do, where you operate and which markets you want to explore.",
    "02-business-profile",
  ],
  [
    "Discover matches",
    "Find a reason to connect.",
    "Explore buyers, suppliers, distributors, investors and partners with clear explanations of potential fit.",
    "03-discover-matches",
  ],
  [
    "Request an introduction",
    "Start with mutual interest.",
    "Send a focused request. The intended workflow requires both businesses to agree before sharing private contact details.",
    "04-request-introduction",
  ],
  [
    "Manage opportunities",
    "Keep the conversation moving.",
    "Organize your next steps and track promising opportunities in one workspace.",
    "05-manage-opportunities",
  ],
];
export function How() {
  return (
    <>
      <section className="page-intro section">
        <Eyebrow>HOW KOBENTRA WORKS</Eyebrow>
        <h1>
          Five steps.
          <br />A world of <em>possibility.</em>
        </h1>
        <p>
          A simple path from business ambition to a meaningful introduction.
        </p>
        <p className="notice">
          A fictional, illustrative journey. The people pictured represent
          different business professionals, not one customer or a real case
          study.
        </p>
      </section>
      <div className="journey section">
        {steps.map(([title, headline, body, file], i) => (
          <article className="journey-step" key={file}>
            <Picture
              file={`how-it-works/how-it-works-${file}.png`}
              alt={`Illustration of ${title.toLowerCase()} with a business professional and conceptual interface`}
            />
            <div>
              <span className="step-number">0{i + 1}</span>
              <Eyebrow>{title}</Eyebrow>
              <h2>{headline}</h2>
              <p>{body}</p>
              {i === 4 && <Cta to="/demo">Try the local demo</Cta>}
            </div>
          </article>
        ))}
      </div>
      <section className="final-cta section">
        <h2>
          Make room for
          <br />
          your next connection.
        </h2>
        <Cta />
      </section>
    </>
  );
}
export function Audience({ organizer = false }: { organizer?: boolean }) {
  const folder = organizer ? "organizers" : "businesses";
  return (
    <>
      <section className="page-intro split-intro section">
        <div>
          <Eyebrow>
            {organizer ? "FOR EVENT ORGANIZERS" : "FOR BUSINESSES"}
          </Eyebrow>
          <h1>
            {organizer ? (
              <>
                Bring people together.
                <br />
                Make business <em>happen.</em>
              </>
            ) : (
              <>
                Your ambition.
                <br />A bigger <em>network.</em>
              </>
            )}
          </h1>
          <p>
            {organizer
              ? "Create the conditions for valuable conversations before, during and after your event."
              : "From your first commercial partner to your next market, discover connections with a purpose."}
          </p>
          <Cta />
        </div>
        <Picture
          priority
          file={`${folder}/${organizer ? "for-event-organizers-event-management" : "for-businesses-discover-partners"}.png`}
          alt={
            organizer
              ? "Business event organizer with illustrative event-management artwork"
              : "Business professionals discussing growth with illustrative platform artwork"
          }
        />
      </section>
      <section className="section">
        <div className="section-heading">
          <h2>
            {organizer ? "Beyond attendance." : "Built for the way"}
            <br />
            <em>{organizer ? "Toward opportunity." : "you do business."}</em>
          </h2>
          <p>
            {organizer
              ? "Kobentra’s proposed event experience focuses on relevance and meaningful introductions. Availability depends on future implementation and integration validation."
              : "Different businesses. Different goals. A shared ambition to find the right people."}
          </p>
        </div>
        <div className="usecases">
          {(organizer
            ? [
                [
                  "Relevant discovery",
                  "Help the right businesses discover your event through sector, location and commercial interests.",
                ],
                [
                  "Purposeful introductions",
                  "A planned consent-based path for attendees to connect around shared goals.",
                ],
                [
                  "Clear follow-through",
                  "Give participants a place to organize the opportunities that begin in your event.",
                ],
                [
                  "Honest integration status",
                  "EventSpark is planned and not connected. Sandbox access, licensing and supported capabilities need verification.",
                ],
              ]
            : [
                [
                  "Entrepreneurs",
                  "Find the commercial relationships to take your business into its next chapter.",
                ],
                [
                  "Manufacturers",
                  "Explore potential distribution partners and relevant buyers for your products.",
                ],
                [
                  "Distributors",
                  "Discover suppliers aligned with your sector and target markets.",
                ],
                [
                  "Buyers",
                  "Explore potential supply relationships and start a focused conversation.",
                ],
              ]
          ).map(([title, body], i) => (
            <article key={title}>
              <span>0{i + 1}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="section audience-story">
        <Picture
          file={`${folder}/${organizer ? "for-event-organizers-attendee-engagement" : "for-businesses-growth-opportunities"}.png`}
          alt={
            organizer
              ? "Event professional at a business conference with conceptual attendee engagement artwork"
              : "Entrepreneur considering business growth with illustrative opportunity artwork"
          }
        />
        <div>
          <Eyebrow>
            {organizer
              ? "THE VALUE OF THE ROOM"
              : "A WORLD BEYOND YOUR CONTACTS"}
          </Eyebrow>
          <h2>
            {organizer
              ? "The right conversation can change everything."
              : "Let’s open your next door."}
          </h2>
          <p>
            {organizer
              ? "Event discovery and connection workflows are part of the Kobentra roadmap. No event records or attendee outcomes shown here are live."
              : "Define what matters to your business, explore sample matches and see how an introduction could begin."}
          </p>
          <Cta to="/demo">Explore the local demo</Cta>
        </div>
      </section>
    </>
  );
}
export function Platform() {
  return (
    <>
      <section className="page-intro section">
        <Eyebrow>THE KOBENTRA PLATFORM</Eyebrow>
        <h1>
          One place for
          <br />
          your next <em>possibility.</em>
        </h1>
        <p>
          Business profiles. Relevant discovery. Consensual introductions. A
          clearer view of what comes next.
        </p>
      </section>
      <section className="section platform-image">
        <Picture
          priority
          file="platform/platform-connected-business-ecosystem.png"
          alt="Conceptual Kobentra business ecosystem artwork featuring a business professional"
        />
        <div>
          <Eyebrow>YOUR WORKSPACE</Eyebrow>
          <h2>
            Built around
            <br />
            your business.
          </h2>
          <p>
            Ordinary Kobentra users won’t need Salesforce accounts. The product
            is designed around a secure Kobentra backend serving businesses in
            one centrally managed platform.
          </p>
          <Cta to="/demo">Open the local demo</Cta>
        </div>
      </section>
      <section className="section architecture">
        <Eyebrow>BEHIND THE CONNECTION</Eyebrow>
        <h2>
          Clear boundaries.
          <br />
          <em>Responsible foundations.</em>
        </h2>
        <div className="architecture-flow">
          <div>
            <Network />
            <h3>Kobentra experience</h3>
            <p>
              Business profiles, market preferences and opportunity tracking.
            </p>
          </div>
          <ArrowRight />
          <div>
            <ShieldCheck />
            <h3>Secure Kobentra backend</h3>
            <p>
              Membership authorization, scoped queries and consent enforcement.
            </p>
          </div>
          <ArrowRight />
          <div>
            <Globe2 />
            <h3>Integration adapters</h3>
            <p>
              Salesforce: not connected.
              <br />
              EventSpark: planned, not connected.
            </p>
          </div>
        </div>
        <div className="two-copy">
          <article>
            <h3>Tenant isolation is our responsibility.</h3>
            <p>
              Organizations are separated through application authorization and
              tenant-scoped integration contracts. Salesforce does not
              automatically isolate Kobentra’s customers. Private contact
              release is reserved for a future server-enforced, mutually
              accepted workflow.
            </p>
          </article>
          <article>
            <h3>A deliberate integration boundary.</h3>
            <p>
              Salesforce secrets and OAuth tokens stay server-side. EventSpark
              capabilities, licensing and sandbox availability remain unverified
              for this implementation. Phase 1 makes no external integration
              calls.
            </p>
          </article>
        </div>
        <details>
          <summary>
            What can I use in this preview?
            <ChevronDown size={18} />
          </summary>
          <p>
            Browse public pages, validate local forms and explore fictional data
            in the clearly labeled demo. Authentication, shared business
            discovery, real introductions and integrations are not connected.
          </p>
        </details>
        <details>
          <summary>
            Who can see my business information?
            <ChevronDown size={18} />
          </summary>
          <p>
            No real business data should be entered in this Phase 1 preview.
            Demo data stays in this browser session; a future directory will
            require explicit publication controls and server-enforced
            authorization.
          </p>
        </details>
      </section>
    </>
  );
}
