# VPN mobile Sites version 11 — deployed, phone acceptance deferred

## User-approved scope

Align the VPN mobile channel with shared mainland fixes and existing speed profile. Do not change the frozen desktop channel or redeploy mainland. No paid model tests; user will test with the next genuine question.

## Release evidence

- URL: https://guanxiang-mobile.abaloyuan.chatgpt.site
- Sites project: appgprj_6a9844ebd4ec819187c4114a11dcc759
- Previous version: 10, source e764e0f73e7b03176e45b94b471f728cb2fdd054
- New version: 11
- New source: f5f6d8cf2eb2f076e9cb43237643b94b31594db3
- Source checkout: C:/Users/27622/.codex/worktrees/80c8/guanxiang-mobile-sites-source
- Saved version ID: appgprj_6a9844ebd4ec819187c4114a11dcc759~appgver_4d38cdcab9c481919e92e67f1d2a1ad1
- Deployment ID: appgdep_6a9d43f44e188191a928cdb27d3288a4
- Status: succeeded, 2026-09-06T10:44:20.794106+00:00
- Environment revision: 4. Only GUANXIANG_ENGINE_PREFLIGHT=true and GUANXIANG_READING_PROFILE=concise-medium-v1 added; all previous entries verified unchanged.

## Shared changes

iPhone entry images and failure fallback, narrow numeric inputs and keyboard guidance, truthful progress, bounded original-task query recovery and no replay of uncertain submissions, backend health preflight, negotiated concise-medium-v1 configuration. The existing accepted button/canvas height lock stays unchanged.

Sites-specific Worker, D1, auth/public access gates, rate limits, manifest origin, service worker and dependency locks remain unchanged. No backend or deterministic engine changes. No frozen desktop changes. No mainland redeployment.

## Verification

- Production Worker build passed; TypeScript check passed.
- 52 Node tests plus 33 TypeScript tests passed, all offline/fixture-based (85 total).
- Python contract fixture uses real deterministic preparation and HTTP transport with stubbed model output: zero paid model calls.
- Live homepage and service-wakeup configuration: HTTP 200.
- Live GuanxiangApp-C6IHsObE.js: HTTP 200 and exact text match to the tested local bundle; recovery and entry fallback markers verified.
- Three revised P1 media files: HTTP 200 and expected image MIME types.
- Backend read-only health advertises concise-medium-v1 and commit 8e1e2dafd843.

## Acceptance boundary

Implementation and deployment checks are complete, not a claim of real-phone end-to-end acceptance or a measured VPN generation latency. Wait for the user's next genuine question; do not generate paid test readings proactively.

## Rollback

Remove the two new environment keys and redeploy saved version 10 if a full rollback is needed. Version 10 remains available, no schema migration was introduced.
