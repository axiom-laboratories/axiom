---
phase: 20-container-infrastructure-routing
plan: "02"
subsystem: infra
tags: [caddy, nginx, docs, cloudflare-access, routing, mkdocs]

# Dependency graph
requires:
  - phase: 20-01
    provides: docs container image (nginx + MkDocs static build) with nginx.conf using alias for /docs/ location
provides:
  - Caddy handle /docs/* routing to docs container in both :443 and :80 virtual hosts
  - Smoke-tested end-to-end: /docs/ and deep asset URLs return 200 over plain HTTP
  - CF Access application (manual) protecting /docs and /docs/* paths at Cloudflare edge
affects:
  - 21-openapi-generation (docs accessible, can write content)
  - 22-content-authoring (docs reachable for content review)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Caddy handle (not handle_path) preserves /docs/ prefix for nginx alias subpath routing"
    - "CF Access at Cloudflare edge is sole access control gate — no Caddy-level auth needed"

key-files:
  created: []
  modified:
    - puppeteer/cert-manager/Caddyfile

key-decisions:
  - "handle /docs/* used in both :443 and :80 Caddy blocks — handle_path would strip prefix and break nginx alias"
  - "CF Access protection for /docs/* deferred by user decision — local routing confirmed working, CF Access to be configured in a future session"

patterns-established:
  - "Caddy block ordering: specific handles (/api, /auth, /ws, /docs) before generic dashboard fallback handle"

requirements-completed:
  - INFRA-04
  - INFRA-05

# Metrics
duration: 10min
completed: 2026-03-16
---

# Phase 20 Plan 02: Caddy /docs Routing and Cloudflare Access Summary

**Caddy handle /docs/* routing wired in both :443 and :80 blocks, smoke-tested locally; CF Access protection deferred by user decision to a future session**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-16T21:42:00Z
- **Completed:** 2026-03-16
- **Tasks:** 2 of 3 complete (Task 3 deferred — CF Access skipped per user decision)
- **Files modified:** 1

## Accomplishments
- Added `handle /docs/* { reverse_proxy docs:80 }` to both `:443` and `:80` Caddy virtual hosts, positioned before the dashboard fallback
- Rebuilt cert-manager container and smoke-tested: `http://localhost/docs/` returns 200, `http://localhost/docs/assets/stylesheets/main.484c7ddc.min.css` returns 200 (nginx alias subpath routing confirmed working)
- Task 3 (CF Access) deferred by user decision — CF Access will be configured in a separate future session

## Task Commits

Each task was committed atomically:

1. **Task 1: Add handle /docs/* routing to Caddyfile** - `51adca7` (feat)
2. **Task 2: Smoke test routing** - no code change (validation only, covered by Task 1 commit)

**Plan metadata:** (this commit — plan marked complete with CF Access deferred)

## Files Created/Modified
- `puppeteer/cert-manager/Caddyfile` - Added handle /docs/* block in both :443 and :80 virtual hosts, before dashboard fallback

## Decisions Made
- Used `handle` (not `handle_path`) in both Caddy blocks — this is critical: `handle_path` strips the `/docs/` prefix before proxying, so nginx receives `/assets/...` which doesn't match the `location /docs/` block → 404. `handle` preserves the full URI.
- No Caddy-level auth added for docs — CF Access at the Cloudflare edge is the sole gate per locked CONTEXT.md decision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test URL in plan used non-existent filename main.css**
- **Found during:** Task 2 (smoke test)
- **Issue:** Plan's verification command used `main.css` but MkDocs Material generates content-hashed CSS (`main.484c7ddc.min.css`). The plain `main.css` returns 404, but the actual CSS files load correctly.
- **Fix:** Verified the correct hashed filename instead; confirmed index.html references only hashed filenames, all of which return 200.
- **Files modified:** None
- **Verification:** `curl http://localhost/docs/assets/stylesheets/main.484c7ddc.min.css` returns 200
- **Committed in:** Covered by Task 1 commit (no code change needed)

---

**Total deviations:** 1 (plan test URL used wrong filename — routing works correctly)
**Impact on plan:** No code impact. Routing verified with correct asset URLs.

## Issues Encountered
- Plan verification URL `main.css` doesn't exist — MkDocs Material uses content-hashed CSS filenames. Confirmed routing works by testing actual filenames extracted from index.html.

## User Setup Required (Deferred)

**CF Access configuration is deferred by user decision.** When ready to protect `/docs/*`, configure in Cloudflare Zero Trust dashboard:

1. Go to Zero Trust Dashboard → Access → Applications → Add application → Self-hosted
2. Application name: Master of Puppets Docs
3. Domain: dev.master-of-puppets.work
4. Path: `/docs` (no wildcard — covers bare /docs)
5. Add second path: `/docs/*` (covers all subpaths)
6. Policy: reuse the same allow policy as the existing dashboard application
7. Verify: private window to https://dev.master-of-puppets.work/docs/ shows CF Access challenge

Note: Until this is configured, `/docs/*` is publicly reachable via the Cloudflare tunnel. No sensitive content is live yet, so risk is low.

## Next Phase Readiness
- Caddy routing is ready — docs reachable at /docs/ on the server
- CF Access protection should be configured before any sensitive documentation content goes live
- Phase 21 (OpenAPI export) can proceed — routing is stable and does not need to change

---
*Phase: 20-container-infrastructure-routing*
*Completed: 2026-03-16*
