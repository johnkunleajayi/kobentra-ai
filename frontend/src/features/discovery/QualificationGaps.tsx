export function QualificationGaps({
  gaps,
}: {
  gaps: { code: string; recommendation: string }[];
}) {
  return (
    <aside className="discovery-own-gaps">
      <details>
        <summary>
          Prepare your business for the next step · {gaps.length} gaps
        </summary>
        <ul>
          {gaps.map((gap) => (
            <li key={gap.code}>
              <strong>{gap.code.replace(/_/g, " ")}</strong>
              <br />
              {gap.recommendation}
            </li>
          ))}
        </ul>
      </details>
    </aside>
  );
}
