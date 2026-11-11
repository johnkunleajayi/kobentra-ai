# Phase 2E checkpoint

Workspace routes: `/workspace` and `/workspace/:businessId/*`, with profile,
preferences and opportunity sections. A single business redirects automatically;
multiple businesses use explicit selection. A membership-backed switcher uses
organization IDs. Switching remounts feature state, clears drafts and ignores old
responses, including completed writes that must not navigate back to the old business.

API additions (existing cookie-session authentication):

- `GET /api/businesses/{business_id}` — authorized workspace/profile.
- `GET|PUT /api/businesses/{business_id}/market-preferences` — `{preferences:
  [{country, partner_type}]}`; PUT atomically replaces that business's preferences.
- `GET|POST /api/businesses/{business_id}/opportunities` — private list/create.
- `GET|PUT /api/businesses/{business_id}/opportunities/{opportunity_id}` — detail/update.

Existing models and revision history are unchanged. Preferences support country
(80 characters) and partner type (40), with up to 50 unique pairs per save. Sectors,
objectives and preferred opportunity types need future schema planning.
Opportunities support title (160) and the existing exploring/conversation/closed
stages. Description, target market/sector and opportunity type are not stored or
presented as implemented. No deletion, public discovery, matching or introductions
were added; future sections are labeled upcoming.

Authorization reuses existing membership helpers on every request. Owners/admins
write; members read. Reads and record lookups are scoped by organization. Writes
require the existing trusted-Origin/JSON CSRF policy and atomic transactions. Per-
organization locks serialize writes; exact title/stage create retries reuse the
existing opportunity. Preference saves are idempotent replacements; concurrent
saves and edits use last-committed-write behavior, without an edit-version field.
No client-supplied owner or organization is accepted in write bodies.

Validation: 114 backend tests passed, scoped Ruff lint/format passed, frontend lint,
typecheck, 8 unit tests and production build passed. Ten focused browser scenarios
were verified (nine passed initially; the remaining opportunity scenario passed
after fixing its status-combobox test locator). These include Phase 2D/account/demo
regressions, single/multiple business selection, switching, saved preference reload,
opportunity create/detail/edit, read-only membership and late-write isolation.
Mobile/light and desktop/dark screenshots in `work/` were visually inspected.
One existing Starlette/httpx deprecation warning remains.

Tests used disposable SQLite databases and mocked browser API responses. No live
Neon connection, mutation or migration was performed; the existing SoftCode
Technologies record was not accessed or changed. PostgreSQL live persistence and
concurrency were not exercised. No dependencies, commit, push, deployment or ISV
integration were introduced. Existing Phase 2D changes and backup folders remain.

Manual verification (two PowerShell terminals, existing environment configuration):

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log
```

```powershell
Set-Location D:\kobentra-ai\frontend
npm run dev -- --port 5173 --strictPort
```

Open `http://127.0.0.1:5173/account`, sign in, then Open workspace. Use a separately
registered business for testing so SoftCode Technologies remains unchanged. Add a
country/partner preference, save and reload. Create an opportunity, open its detail,
edit its title/status, and reload. Switch businesses: preferences/opportunities must
be separate. Sign out/in and confirm the selected authorized workspace retrieves
saved records. These manual actions intentionally persist to the configured database.
The already-running frontend preview was reused and left running.
