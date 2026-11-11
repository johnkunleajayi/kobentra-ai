import { Compass, RotateCw } from "lucide-react";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import { discoveryPath } from "./api";
import { PartnerCard } from "./PartnerCard";
import { QualificationGaps } from "./QualificationGaps";
import type { DiscoveryResponse } from "./types";
import "./discovery.css";

export function DiscoveryPage({
  businessId,
  country,
}: {
  businessId: string;
  country: string;
}) {
  const resource = useResource<DiscoveryResponse>(discoveryPath(businessId));
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
          Provisional discovery · Identity verification required
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
                {resource.data.directory_status === "not_configured"
                  ? "Discovery is awaiting publication approval"
                  : "No cross-border partners to show yet"}
              </h3>
              <p>
                {resource.data.directory_status === "not_configured"
                  ? "The approved discovery directory has not been configured. Registering a business does not automatically publish it."
                  : "No approved businesses in another country are currently available. Your private business data remains within your workspace."}
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
            Rules: {resource.data.rules_version}. Scores describe compatibility
            under partial evidence, never a verified partnership.
          </p>
        </>
      )}
    </section>
  );
}
