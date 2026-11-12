import { useEffect, useRef, useState } from "react";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import {
  assessmentsPath,
  initiateAssessment,
  launchAssessment,
  type Assessment,
  type AssessmentConfig,
  type Launch,
} from "./api";
import { AssessmentHistory } from "./AssessmentHistory";
import { NativeAssessment } from "./NativeAssessment";

export function AssessmentsPage({
  businessId,
  writable,
}: {
  businessId: string;
  writable: boolean;
}) {
  const config = useResource<AssessmentConfig>(
    `${assessmentsPath(businessId)}/config`,
  );
  const history = useResource<{ assessments: Assessment[] }>(
    assessmentsPath(businessId),
  );
  const refreshHistory = history.retry;
  useEffect(() => {
    const refresh = (event: Event) => {
      if ((event as CustomEvent).detail === businessId) refreshHistory();
    };
    window.addEventListener("kobentra-assessment-processed", refresh);
    return () =>
      window.removeEventListener("kobentra-assessment-processed", refresh);
  }, [businessId, refreshHistory]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [launch, setLaunch] = useState<Launch | null>(null);
  const pending = useRef(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  if (!config.data || !history.data)
    return (
      <>
        <h2>Assessments</h2>
        <ResourceState
          error={config.error || history.error}
          retry={() => {
            config.retry();
            history.retry();
          }}
        />
      </>
    );
  if (config.data.synchronization === "salesforce_flow")
    return (
      <>
        <h2>{config.data.title}</h2>
        <p>Provider: Salesforce / SurveyVista</p>
        {config.data.configured ? (
          <NativeAssessment
            businessId={businessId}
            assessments={history.data.assessments}
            writable={writable}
            refresh={history.retry}
          />
        ) : (
          <p role="status">Salesforce is not configured.</p>
        )}
        <AssessmentHistory assessments={history.data.assessments} />
      </>
    );
  return (
    <>
      <h2>{config.data.title}</h2>
      <p>Provider: {config.data.provider}</p>
      <p className="notice">
        This public SurveyVista form collects anonymous responses. Its shared
        link does not identify this business. Salesforce response
        synchronization is not connected; opening or returning from the form
        never confirms completion.
      </p>
      {!config.data.configured && (
        <p role="status">
          Assessment launching is not configured. Contact your administrator.
        </p>
      )}
      {writable && (
        <button
          className="button"
          disabled={busy || !config.data.configured}
          onClick={async () => {
            if (pending.current) return;
            pending.current = true;
            setBusy(true);
            setError("");
            setLaunch(null);
            try {
              const assessment = await initiateAssessment(businessId);
              // Stop if business context changed before the launch request.
              if (!active.current) return;
              const result = await launchAssessment(businessId, assessment.id);
              if (active.current) {
                setLaunch(result);
                history.retry();
              }
            } catch (err) {
              if (active.current)
                setError(
                  err instanceof Error
                    ? err.message
                    : "Unable to start assessment.",
                );
            } finally {
              pending.current = false;
              if (active.current) setBusy(false);
            }
          }}
        >
          {busy ? "Preparing assessment…" : "Start assessment"}
        </button>
      )}
      {error && <p role="alert">{error}</p>}
      {launch && (
        <div className="workspace-note">
          <p role="status">Launch prepared. Completion remains unverified.</p>
          <a
            className="button"
            href={launch.launch_url}
            target="_blank"
            rel="noopener noreferrer"
            referrerPolicy="no-referrer"
          >
            Open SurveyVista assessment ↗
          </a>
          <p className="small-copy">
            Opens a shared public form in a new tab. No Kobentra business or
            user identifier is appended.
          </p>
        </div>
      )}
      <p>
        Repeated starts reuse this business’s pending assessment for the
        configured survey.
      </p>
      <AssessmentHistory assessments={history.data.assessments} />
      <button className="secondary" onClick={history.retry}>
        Refresh assessment history
      </button>
    </>
  );
}
