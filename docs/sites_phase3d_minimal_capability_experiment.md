# Phase 3D minimal capability experiment design

Status: `DESIGNED_NOT_EXECUTED`  
Depends on: Phase 3C ADR decision D  
Single unknown: Can a private, non-deployed Sites preview make an allowlisted cross-origin HTTPS JSON request?

## Purpose

Resolve only the highest-value unknown blocking Architecture Option A. This is a disposable platform-capability test, not an application prototype, engine integration, API test, release rehearsal or deployment.

## Preconditions and manual authorization

Do not begin unless the user explicitly authorizes all of the following in the execution turn:

1. creation of one temporary Sites test project;
2. use of a private/owner-only preview, with no deployment or public access;
3. transmission of one synthetic JSON object to a named HTTPS test endpoint;
4. inspection of browser network/console results;
5. deletion of the temporary Site and test-endpoint data.

Also confirm workspace policy permits a private Site and that the endpoint owner approves the exact origin. If the Sites interface requires a save or deployment to obtain a runnable URL, stop: every deployment is production and is outside this experiment design.

## Experiment input

Use only this synthetic payload or an equivalently inert value:

```json
{
  "experiment": "phase3d-cross-origin-fetch",
  "nonce": "synthetic-001",
  "value": 7
}
```

The response should echo only `nonce` and return a fixed boolean such as `accepted: true`. Do not use Contract V1 fields, divination numbers, questions, birth information, repository content, user data, API keys, OpenAI credentials or model prompts.

## Minimal artifacts

- One temporary Site containing a single button, a status element and minimal browser JavaScript.
- One pre-approved disposable HTTPS JSON echo endpoint that stores nothing and permits only the observed private-preview origin.
- One local, redacted observation record containing timestamps, HTTP status, browser error category, response shape and cleanup confirmation.

No Python engine, repository import, D1, R2, hosted secret, authentication system, custom domain or OpenAI Responses API is used.

## Procedure

1. Reconfirm the experiment is owner-only/private and has not been deployed.
2. Record the preview origin without recording personal URL path components in the permanent report.
3. Configure the disposable endpoint to allow exactly that origin and `POST, OPTIONS` with `Content-Type: application/json`; do not allow credentials.
4. From the temporary page, make exactly one user-triggered `fetch` POST containing the synthetic payload.
5. Record the OPTIONS result if a preflight occurs, the POST status, whether JavaScript can read the JSON response, and any CSP/CORS/browser error category.
6. Do not retry automatically. A timeout or ambiguous network state is `INCONCLUSIVE`.
7. Delete endpoint data/configuration and the temporary Site through supported interfaces.
8. Verify the Site is absent, the endpoint contains no request body/log retention beyond the approved observation, and no public URL was created.

## Success criteria

All must be true:

- the page remains private and non-deployed;
- one synthetic request reaches the intended HTTPS origin;
- any preflight succeeds with the exact preview origin;
- the POST returns the expected status and JSON shape;
- browser JavaScript can read and display the response;
- no secret or real data is transmitted;
- cleanup verification succeeds.

Result: `CROSS_ORIGIN_FETCH_CONFIRMED_FOR_OBSERVED_PREVIEW_CONTEXT`.

This result confirms only the observed account, preview context, origin and date. It does not prove production suitability, stable origins, load capacity or security compliance.

## Failure and stop criteria

- CSP blocks the destination: `FAILED_CSP`.
- Browser CORS/preflight blocks the request: `FAILED_CORS`.
- Sites requires a deployment/public URL to run the test: `BLOCKED_REQUIRES_PRODUCTION_DEPLOYMENT`.
- Workspace or interface approval is unavailable: `BLOCKED_APPROVAL`.
- The endpoint cannot restrict the allowed origin: `BLOCKED_UNSAFE_ENDPOINT`.
- Network outcome is ambiguous or times out: `INCONCLUSIVE_NETWORK`; do not retry automatically.
- Any prompt to provide a key, real data, repository source or wider access: stop with `SCOPE_VIOLATION`.

No failure authorizes switching to Option B, changing CORS broadly, deploying a proxy or creating a public Site.

## Data produced and retention

The only retained report fields are:

- experiment/result code;
- date and Sites capability/tool version if visible;
- redacted origin category, not a personal absolute path;
- request count;
- preflight/POST status and latency;
- CSP/CORS/browser error category;
- response schema match boolean;
- Site and endpoint cleanup booleans.

Do not retain raw browser profiles, cookies, authorization headers, full URLs with identifiers, request headers, repository files or endpoint logs.

## Cleanup

1. Delete the temporary Site using the supported Sites interface. If deletion is unavailable, remove access and stop with `CLEANUP_BLOCKED`; do not claim completion.
2. Remove the endpoint origin allowlist and delete its ephemeral logs/data.
3. Verify no deployment/version intended for production was created.
4. Record cleanup booleans without embedding credentials or private URLs.

## Decision mapping

| Experiment result | ADR action |
|---|---|
| Confirmed | Revisit Option A with a separate security and operations review; do not implement automatically. |
| `FAILED_CSP` or `FAILED_CORS` | Keep D; research documented configuration support before any new experiment. |
| Requires production deployment | Keep D; request a new, explicitly scoped approval only if the user wishes to continue. |
| Blocked, inconclusive or cleanup blocked | Keep D and stop for human handling. |

Phase 3D is not executed by this document and must never start automatically.
