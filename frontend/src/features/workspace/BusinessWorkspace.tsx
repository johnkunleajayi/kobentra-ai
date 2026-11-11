import {
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useParams,
} from "react-router-dom";
import "./workspace.css";
import type { Business } from "../business/types";
import { BusinessSummary } from "../business/BusinessSummary";
import { PreferencesPage } from "../market-preferences/PreferencesPage";
import { OpportunitiesPage } from "../opportunities/OpportunitiesPage";
import { OpportunityDetail } from "../opportunities/OpportunityDetail";
import { AssessmentsPage } from "../assessments/AssessmentsPage";
import { businessPath } from "./api";
import { useResource } from "./useResource";
import { ResourceState } from "./ResourceState";
import { BusinessSwitcher } from "./BusinessSwitcher";

export function BusinessWorkspace() {
  const { businessId = "" } = useParams();
  // A business switch unmounts every previous feature, draft and pending response.
  return <WorkspaceContent key={businessId} businessId={businessId} />;
}
function WorkspaceContent({ businessId }: { businessId: string }) {
  const { pathname } = useLocation();
  const business = useResource<Business>(businessPath(businessId));
  const memberships = useResource<{ businesses: Business[] }>(
    "/api/businesses",
  );
  if (!business.data || !memberships.data)
    return (
      <section className="section">
        <h1>Business workspace</h1>
        <ResourceState
          error={business.error || memberships.error}
          retry={() => {
            business.retry();
            memberships.retry();
          }}
        />
      </section>
    );
  const active = business.data;
  const writable = ["owner", "admin"].includes(active.role);
  return (
    <section className="real-workspace">
      <aside className="real-workspace-sidebar">
        <BusinessSwitcher
          businesses={memberships.data.businesses}
          active={businessId}
        />
        <nav aria-label="Business workspace navigation">
          <NavLink end to={`/workspace/${businessId}`}>
            Overview
          </NavLink>
          <NavLink to={`/workspace/${businessId}/profile`}>
            Business profile
          </NavLink>
          <NavLink to={`/workspace/${businessId}/preferences`}>
            Market preferences
          </NavLink>
          <NavLink to={`/workspace/${businessId}/opportunities`}>
            Opportunities
          </NavLink>
          <span>Matches · Upcoming</span>
          <NavLink to={`/workspace/${businessId}/assessments`}>Assessments</NavLink>
          <span>Introductions · Upcoming</span>
        </nav>
        <Link to="/workspace">All workspaces</Link>
        <Link to="/account">My account</Link>
        <Link to="/business/onboarding">Register another business</Link>
      </aside>
      <div className="real-workspace-content">
        <header className="workspace-heading">
          <div>
            <span className="eyebrow">BUSINESS WORKSPACE · {active.role}</span>
            <h1>{active.name}</h1>
          </div>
        </header>
        {!writable && (
          <p className="notice">Your membership has read-only access.</p>
        )}
        <Routes>
          <Route
            index
            element={
              <>
                <h2>Your business, in motion.</h2>
                <p>
                  Manage private market preferences and opportunities for{" "}
                  {active.name}.
                </p>
                <div className="real-workspace-grid">
                  <Link
                    className="workspace-note"
                    to={`/workspace/${businessId}/preferences`}
                  >
                    <h3>Shape your target markets</h3>
                    <p>Choose countries and the kinds of partners you seek.</p>
                  </Link>
                  <Link
                    className="workspace-note"
                    to={`/workspace/${businessId}/opportunities`}
                  >
                    <h3>Move opportunities forward</h3>
                    <p>Create and manage your private commercial pipeline.</p>
                  </Link>
                </div>
                <p>
                  Partner matching and introductions are upcoming. No
                  connections are sent from this workspace.
                </p>
              </>
            }
          />
          <Route
            path="profile"
            element={<BusinessSummary business={active} />}
          />
          <Route path="assessments" element={<AssessmentsPage businessId={businessId} writable={writable} />} />
          <Route
            path="preferences"
            element={
              <PreferencesPage businessId={businessId} writable={writable} />
            }
          />
          <Route
            path="opportunities"
            element={
              <OpportunitiesPage business={active} writable={writable} />
            }
          />
          <Route
            path="opportunities/:opportunityId"
            element={
              <OpportunityDetail
                key={pathname}
                business={active}
                writable={writable}
              />
            }
          />
          <Route
            path="*"
            element={
              <p>
                This workspace section is unavailable. Use the navigation to
                continue.
              </p>
            }
          />
        </Routes>
      </div>
    </section>
  );
}
