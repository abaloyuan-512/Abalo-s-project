# ADR: Sites integration architecture

- Status: `DECIDED_FOR_RESEARCH_GATE`
- Decision: `D. INSUFFICIENT_EVIDENCE_TO_SELECT`
- Date: 2026-07-13
- Baseline: `25cb5bd3daa02a923f3f7d7d932b2c176e8d4a81`

## Context

Phase 3B proved a local, keyless browser UI that posts Contract V1 JSON to a same-origin Python loopback server. The server delegates deterministic calculation to the existing authoritative Python engine. Phase 3C asks how that boundary could be hosted with OpenAI Sites without changing deterministic rules, knowledge state, release status or Contract V1.

The capability audit is in [sites_phase3c_capability_audit.md](sites_phase3c_capability_audit.md). Official product guidance confirms compatible existing projects, a JS/ESM server runtime, runtime variables/secrets, D1/R2, access control, domains and versions. It does not establish the end-to-end cross-origin browser path or a native Python runtime.

## Constraints

- Python remains the authoritative deterministic engine; AI never participates in chart calculation.
- Contract V1, its schemas, error semantics and release gate remain frozen.
- `NarrativeReleaseStatus` remains `UNVERIFIED`.
- No API key or privileged credential may reach browser code.
- Phase 3C cannot create, upload, save, deploy or publish a Site.
- Phase 3C cannot deploy a mock or Python API or transmit private repository content.
- A capability is not selected merely because it is plausible on a generic web platform.

## Confirmed facts

1. Sites can host interactive web applications and compatible existing source projects.
2. The current Sites build contract uses a Cloudflare Worker-compatible JavaScript/ESM server artifact.
3. Hosted runtime variables and secrets, D1, R2, access control, custom domains and saved/deployed versions exist.
4. Saving a version and deploying a version are distinct; every deployment URL is production.
5. The Phase 3B frontend has no key and calls same-origin `/api/v1/meihua`.
6. The current Phase 3B server is a Python `ThreadingHTTPServer` and is not a Sites build artifact.

## Unknowns

- Sites preview CSP, cross-origin `fetch` behavior, stable preview origin and external API CORS requirements as an end-to-end path.
- Sites JS server outbound HTTPS/proxy behavior and operating limits.
- Exact no-surprise migration behavior for the raw three-file frontend and root-relative assets.
- Required workspace approval and data-governance settings for a private experiment.

## Options

### A. `SITES_FRONTEND_PLUS_EXTERNAL_PYTHON_API`

The browser-hosted frontend calls an external HTTPS Python API directly. This preserves the Python engine and avoids a second server layer. It requires:

- a separately operated HTTPS service;
- strict Contract V1 validation, origin allowlisting, authentication/abuse controls, rate limits and safe errors;
- a frontend endpoint adapter;
- confirmed Sites preview/deployment origin, CSP and cross-origin behavior.

Status: leading candidate, but blocked by the Phase 3D unknown.

### B. `SITES_FRONTEND_PLUS_THIN_SERVER_ADAPTER_PLUS_EXTERNAL_PYTHON_API`

The browser calls a same-origin Sites JS route, which forwards a validated request to an external Python API. It can isolate backend credentials and CORS from the browser, but adds another trust boundary, latency and failure mode. The Sources confirm the JS server runtime but do not explicitly confirm outbound HTTPS/proxy behavior.

Status: viable only after explicit server-egress evidence; not selected.

### C. `SITES_HOSTED_FULL_STACK_PYTHON`

Sites would execute the authoritative Python engine directly. The current installed Sites contract requires a JS/ESM Worker server artifact and exposes no Python server entry point.

Status: unsupported by the current capability contract; rejected.

### D. `INSUFFICIENT_EVIDENCE_TO_SELECT`

No production architecture is selected until the smallest high-value unknown is resolved with synthetic data.

Status: selected.

## Decision

Select **D. `INSUFFICIENT_EVIDENCE_TO_SELECT`**.

Option A remains the preferred hypothesis because it preserves the current Python authority with the fewest hosted layers. It is not approved for implementation. Phase 3D may test only whether a private, non-deployed Sites preview can make one allowlisted cross-origin HTTPS JSON request. A successful experiment would permit reconsidering A; it would not itself approve deployment or production use.

## Consequences

- No Phase 3B source, Python service, contract or test changes are authorized by this ADR.
- No Site, database, secret, domain, external API or production URL is created.
- Phase 3D needs explicit user/interface authorization before creating a temporary Site or contacting a synthetic endpoint.
- A failed or blocked Phase 3D experiment leaves D in force.
- B requires a separate server-egress experiment; it is not a fallback to execute automatically.
- C cannot be revisited without new official evidence for a supported Python runtime.

## Minimum backend requirements if A is later selected

- HTTPS only; fixed, allowlisted Site origins; no wildcard credentialed CORS.
- Server-side Contract V1 schema validation and deterministic normalization.
- No client-supplied authority, role, release status or audit result is trusted.
- Authentication/abuse controls, per-origin and per-principal rate limits, request-size limits and bounded timeouts.
- Stable error envelopes that never expose stack traces, local paths, secrets or internal prompts.
- Request/audit correlation without storing raw sensitive question text by default.
- Dependency, availability, retention, deletion and incident-response ownership documented.
- No OpenAI Responses call and no narrative release while status is `UNVERIFIED`.

## Security boundary

```text
Browser / Sites page (untrusted input, no secret)
        |
        | Contract V1 over HTTPS; explicit origin policy
        v
External API boundary (auth, limits, validation, audit)
        |
        | typed in-process call
        v
Authoritative deterministic Python engine
```

If B is later considered, the Sites JS server becomes an additional security boundary, not a replacement for validation at the Python API.

## Release restrictions

- No public or private production deployment is approved.
- No real user, account system, OTP, custom domain, database or persistent user record is approved.
- No API key may be placed in frontend code, prompts, `.openai/hosting.json` or documentation.
- No Phase 2C state promotion or narrative release is approved.
- Completing Phase 3D does not authorize beta, closed testing or Sites implementation.

## Revisit conditions

Revisit this ADR only when at least one of the following is available:

1. Phase 3D produces reproducible evidence for the browser-to-external-HTTPS path, including observed origin, CSP/CORS result and cleanup proof.
2. Current official Sites documentation explicitly defines server outbound HTTPS/proxy constraints.
3. Current official Sites documentation adds a supported Python server runtime.
4. Workspace administrators provide the required private-experiment and data-governance approvals.

Any revisit must cite current sources and create a new ADR revision; it must not silently overwrite this evidence boundary.
