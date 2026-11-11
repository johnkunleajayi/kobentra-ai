import { useNavigate } from "react-router-dom";
import type { Business } from "../business/types";

export function BusinessSwitcher({
  businesses,
  active,
}: {
  businesses: Business[];
  active: string;
}) {
  const navigate = useNavigate();
  return (
    <label>
      Active business
      <select
        value={active}
        onChange={(event) => navigate(`/workspace/${event.target.value}`)}
      >
        {businesses.map((business) => (
          <option
            key={business.organization_id}
            value={business.organization_id}
          >
            {business.name}
          </option>
        ))}
      </select>
    </label>
  );
}
