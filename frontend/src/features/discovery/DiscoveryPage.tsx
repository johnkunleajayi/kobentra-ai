import { Compass, RotateCw } from "lucide-react";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import { discoveryPath } from "./api";
import { PartnerCard } from "./PartnerCard";
import { QualificationGaps } from "./QualificationGaps";
import type { DiscoveryResponse } from "./types";
import "./discovery.css";
import { useEffect } from "react";

export function DiscoveryPage({
  businessId,
  country,
}: {
  businessId: string;
  country: string;
}) {
  const resource = useResource<DiscoveryResponse>(discoveryPath(businessId));
  const refreshDiscovery = resource.retry;
  useEffect(() => {
    const update = (event: Event) => {
      if ((event as CustomEvent).detail === businessId) refreshDiscovery();
    };
    const timer = setInterval(() => {
      if (!document.hidden) refreshDiscovery();
    }, 15000);
    window.addEventListener("kobentra-assessment-processed", update);
    return () => {
      clearInterval(timer);
      window.removeEventListener("kobentra-assessment-processed", update);
    };
  }, [businessId, refreshDiscovery]);
  return (
    <section className="partner-discovery" aria-labelledby="discovery-title">
      <header className="discovery-intro">
        <span className="discovery-kicker">CROSS-BORDER CONNECTIONS</span>
        <h2 id="discovery-title">
          Find alignment.
          <br />
          <em>Build with clarity.</em>
        </h2>
        <p>
          Explore potential partners through declared interests and explainable
          compatibility. Start with what we know—and what we still need to
          establish.
        </p>
        <span className="discovery-provisional">
          Provisional business connections
        </span>
      </header>
      {!resource.data ? (
        <div className="discovery-state">
          <ResourceState error={resource.error} retry={resource.retry} />
        </div>
      ) : (
        <>
          <div className="discovery-toolbar">
            <p>
              {resource.data.matches.length} potential{" "}
              {resource.data.matches.length === 1 ? "partner" : "partners"} ·
              From {country}
            </p>
            <button className="secondary" onClick={resource.retry}>
              <RotateCw size={15} aria-hidden="true" /> Refresh discovery
            </button>
          </div>
          {!resource.data.matches.length ? (
            <div className="discovery-state">
              <Compass size={36} aria-hidden="true" />
              <h3>
                {resource.data.discovery_eligible === false
                  ? "Complete your assessment to discover partners"
                  : "No cross-border partners to show yet"}
              </h3>
              <p>
                {resource.data.status_message ||
                  "Eligible businesses appear automatically after assessment processing. No administrator publication is needed."}
              </p>
            </div>
          ) : (
            <div className="partner-results">
              {resource.data.matches.map((match) => (
                <PartnerCard
                  key={match.partner.business_id}
                  match={match}
                  sourceCountry={country}
                />
              ))}
            </div>
          )}
          {resource.data.requester_qualification_gaps.length > 0 && (
            <QualificationGaps
              gaps={resource.data.requester_qualification_gaps}
            />
          )}
          <p className="discovery-rules">
            Matches are based on business-provided information. Verify partner
            details before entering commercial agreements. Rules:{" "}
            {resource.data.rules_version}. Scores describe compatibility under
            partial evidence, never a verified partnership.
          </p>
        </>
      )}
    </section>
  );
}
