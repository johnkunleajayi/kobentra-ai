import type { Assessment } from "./api";

export function AssessmentHistory({
  assessments,
}: {
  assessments: Assessment[];
}) {
  return (
    <>
      <h3>Assessment history</h3>
      {!assessments.length && (
        <p>No assessments have been initiated for this business.</p>
      )}
      {assessments.map((item) => (
        <article className="workspace-note" key={item.id}>
          <span className="badge">
            {item.status === "completed_verified"
              ? "Verified completed"
              : item.status === "launch_requested"
                ? "Launch requested · completion unverified"
                : "Initiated · not yet launched"}
          </span>
          <h3>Partner Qualification Assessment</h3>
          <p>Provider: SurveyVista</p>
          <p>
            Initiated:{" "}
            <time dateTime={item.initiated_at}>
              {new Date(item.initiated_at).toLocaleString()}
            </time>
          </p>
          {item.status === "completed_verified" && item.completed_at ? (
            <p>
              Verified completion:{" "}
              <time dateTime={item.completed_at}>
                {new Date(item.completed_at).toLocaleString()}
              </time>
            </p>
          ) : (
            <p>Completion has not been verified in Salesforce.</p>
          )}
          <p className="small-copy">Internal assessment ID: {item.id}</p>
        </article>
      ))}
    </>
  );
}
