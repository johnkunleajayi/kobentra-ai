import type { Administration } from "./management-types";
export function StatusBadges({ value }: { value?: Administration }) {
  if (!value) return <span>Not recorded</span>;
  return (
    <div className="admin-statuses" aria-label="Administrative statuses">
      <span>Approval: {value.approval}</span>
      <span>Identity: {value.identity}</span>
      <span>Access: {value.access}</span>
    </div>
  );
}
