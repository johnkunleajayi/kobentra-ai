import { Link, useSearchParams } from "react-router-dom";
import { useResource } from "../workspace/useResource";
import { ResourceState } from "../workspace/ResourceState";
import { StatusBadges } from "./StatusBadges";
import {
  dateLabel,
  type AdminPage,
  type AdminUser,
  type AdminBusiness,
} from "./types";

export function AdminDirectory({ kind }: { kind: "users" | "businesses" }) {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const resource = useResource<AdminPage<AdminUser | AdminBusiness>>(
    `/api/admin/${kind}?${new URLSearchParams({ q, page: String(page), page_size: "20" })}`,
  );
  return (
    <>
      <header className="admin-heading">
        <span className="eyebrow">PLATFORM DIRECTORY</span>
        <h1>{kind === "users" ? "Registered users" : "Business network"}</h1>
        <p>
          Read-only records. Creation dates are unavailable where the existing
          schema does not record them.
        </p>
      </header>
      <form
        className="admin-search"
        onSubmit={(event) => {
          event.preventDefault();
          const value = new FormData(event.currentTarget).get("q") as string;
          setParams({ q: value.trim(), page: "1" });
        }}
      >
        <label htmlFor="admin-search">
          {kind === "users"
            ? "Search email"
            : "Search name, country or industry"}
        </label>
        <div>
          <input
            id="admin-search"
            key={q}
            name="q"
            defaultValue={q}
            maxLength={100}
          />
          <button className="button" type="submit">
            Search
          </button>
        </div>
      </form>
      {!resource.data ? (
        <ResourceState error={resource.error} retry={resource.retry} />
      ) : (
        <>
          <p role="status">
            {resource.data.total} records · Page {resource.data.page}
          </p>
          {!resource.data.items.length ? (
            <div className="admin-panel">
              <h2>No {kind} found</h2>
              <p>Try another search or return to the full directory.</p>
            </div>
          ) : (
            <div
              className="admin-table-wrap"
              tabIndex={0}
              role="region"
              aria-label={`${kind} results`}
            >
              <table className="admin-table">
                <caption className="sr-only">Registered {kind}</caption>
                <thead>
                  <tr>
                    {(kind === "users"
                      ? ["Email", "Account created", "Associated businesses"]
                      : [
                          "Business",
                          "Country",
                          "Industry",
                          "Owner",
                          "Registered",
                          "Status",
                        ]
                    ).map((label) => (
                      <th scope="col" key={label}>
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {resource.data.items.map((item) => (
                    <tr key={item.id}>
                      {"email" in item ? (
                        <>
                          <td>{item.email}</td>
                          <td>{dateLabel(item.created_at)}</td>
                          <td>
                            {item.businesses.length
                              ? item.businesses.map((b) => (
                                  <div key={b.business_id}>
                                    <Link
                                      to={`/admin/businesses/${b.business_id}`}
                                    >
                                      {b.name}
                                    </Link>{" "}
                                    · {b.role}
                                  </div>
                                ))
                              : "No memberships"}
                          </td>
                        </>
                      ) : (
                        <>
                          <td>
                            <Link to={`/admin/businesses/${item.id}`}>
                              {item.name}
                            </Link>
                          </td>
                          <td>{item.country}</td>
                          <td>{item.industry}</td>
                          <td>
                            {item.owners.map((o) => o.email).join(", ") ||
                              "Not recorded"}
                          </td>
                          <td>{dateLabel(item.registered_at)}</td>
                          <td>
                            <StatusBadges value={item.administration} />
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <nav className="admin-pagination" aria-label="Directory pagination">
            <button
              className="secondary"
              disabled={page <= 1}
              onClick={() => setParams({ q, page: String(page - 1) })}
            >
              Previous
            </button>
            <span>
              Page {page} of{" "}
              {Math.max(
                1,
                Math.ceil(resource.data.total / resource.data.page_size),
              )}
            </span>
            <button
              className="secondary"
              disabled={page * resource.data.page_size >= resource.data.total}
              onClick={() => setParams({ q, page: String(page + 1) })}
            >
              Next
            </button>
          </nav>
        </>
      )}
    </>
  );
}
