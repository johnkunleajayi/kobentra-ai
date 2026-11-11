# Partner Discovery — milestone 2J

Workspace route: `/workspace/:businessId/discover`. Uses the existing authenticated
`GET /api/businesses/{business_id}/matches`, current business switcher and design
tokens. Displays computed score, coverage, compatible/incompatible/unknown dimensions,
evidence limitations and the introduction restriction. No contacts, assessment answers
or another tenant's readiness score are requested or shown. No introduction action.

## Controlled fictional scenario

`python -m app.demo.discovery` requires an explicit SQLite URL, an existing normally
authenticated local user, and `--approve-fictional-publication`. It refuses PostgreSQL,
memory databases and files outside `D:/kobentra-ai/work/partner-discovery`. It never
loads .env or contacts Salesforce. Registration and preferences use existing authorized
services. Repeating the command reuses unchanged registrations. No real businesses are
published. It prints only fictional business IDs and the approved allowlist; it does
not edit configuration or generate sessions. Partial local preparation can be retried.

Scenario: fictional Lagos packaged-food producer seeks distributors in Ghana;
fictional Accra distributor serving Ghana seeks Nigerian food manufacturers as suppliers.
The latter uses the explicit `Manufacturer` preference. Existing v1 rules recognize
`Distributor`/`Manufacturer`, yielding 100 compatibility at only 62.5% coverage.
Capacity, timing and capability quality remain unknown; introductions stay blocked.
With only the generic `Supplier` preference, this pair would not reach sufficient
coverage for a score. No rule changes or manually assigned scores were made.

## Exact local verification

```powershell
Set-Location D:\kobentra-ai\backend
.\.venv\Scripts\python.exe -m pytest tests/test_discovery_demo.py tests/test_matching.py tests/test_qualification_policy.py -q --basetemp=D:/kobentra-ai/work/pytest-2j
.\.venv\Scripts\python.exe -m ruff check app/demo tests/test_discovery_demo.py
Set-Location D:\kobentra-ai\frontend
npm test
npm run lint
npm run typecheck
npm run build
npx playwright test --config playwright.discovery.config.ts
```

Backend tests generate `work/discovery-fixture.json` using the actual API/engine in an
isolated SQLite fixture. Browser tests replay that fictional API response and mock
authentication; they do not claim live Google/Neon integration verification.

## Optional persistent local demonstration — do not run against Neon

After approval, in a dedicated PowerShell terminal:

```powershell
Set-Location D:\kobentra-ai\backend
New-Item -ItemType Directory -Force D:\kobentra-ai\work\partner-discovery | Out-Null
$env:DATABASE_URL='sqlite+pysqlite:///D:/kobentra-ai/work/partner-discovery/demo.db'
$env:MATCHING_DISCOVERY_BUSINESS_IDS='[]'
$env:SALESFORCE_DISPATCH_ENABLED='false'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log
```

Use the normal Google sign-in at `http://127.0.0.1:5173`; obtain your local user ID
from the authenticated `/api/auth/me` response (never copy cookies/tokens). Stop the
local server and prepare the fictional businesses in that same terminal:

```powershell
$demo = .\.venv\Scripts\python.exe -m app.demo.discovery --database-url $env:DATABASE_URL --owner-user-id '<local-user-id>' --approve-fictional-publication | ConvertFrom-Json
$env:MATCHING_DISCOVERY_BUSINESS_IDS=ConvertTo-Json -InputObject @($demo.matching_discovery_business_ids) -Compress
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --no-access-log
```

Run `npm run dev` from `D:\kobentra-ai\frontend` in another terminal. Select
**Fictional Demo — Lagos Pantry Foods**, then **Partner discovery**. Inspect the
Nigeria→Ghana card, actual score, coverage, explanations and restrictions. Switch
businesses and verify old results clear. The separate local database must remain
selected for this demo; never copy the allowlist into a Neon-connected server.

No production migrations or persistent demo preparations are part of automated validation.

## Milestone 2K verification

The shared footer now omits its signup/account CTA when the existing layout session
state is authenticated. Guest signup and header sign-in navigation remain available;
no additional authentication request is introduced. Focused browser coverage includes
account/public-page footer behavior, desktop/mobile discovery, keyboard disclosure,
loading/error/retry/empty states and business switching. Browser authentication and
API transport are mocked using the actual engine-generated fictional response; this
does not substitute for an approved persistent local Google-login demonstration.
The existing local preparation commands above remain unchanged and require approval.
As of 2L-B, the platform owner must also explicitly approve the fictional candidate
businesses through administration; the demo publication flag does not grant business
approval. Missing decisions default to pending and are not discoverable.
