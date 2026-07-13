# Sites-first Phase 3C capability audit

Status: research complete; implementation not started  
Baseline: `25cb5bd3daa02a923f3f7d7d932b2c176e8d4a81`  
Research date: 2026-07-13

## Scope and classification rules

This audit evaluates whether the Phase 3B local prototype can move to OpenAI Sites without changing the frozen deterministic engine or Contract V1. It does not create, upload, save, deploy, or publish a Site.

Every capability is classified as one of:

- `CONFIRMED`: explicitly supported by a current official source or installed Sites capability contract.
- `UNSUPPORTED`: the current supported project/runtime contract conflicts with the requested capability.
- `UNCONFIRMED`: the available sources do not establish the capability; no inference is permitted.
- `NOT_APPLICABLE`: not needed for the current decision.

## Evidence register

| ID | Source | Used for |
|---|---|---|
| S1 | Installed OpenAI Sites `sites-building` skill, version 0.1.27 | Existing-project workflow, build artifact, JS/ESM server runtime, environment and storage bindings |
| S2 | Installed Sites persistence reference | D1, R2, hosted runtime variables and secrets |
| S3 | Installed Sites authentication reference | Workspace identity headers and Sites-managed authentication boundaries |
| S4 | Current Sites connector schemas inspected in this session | Site creation metadata, versions, deployments, access controls, domains, environment variables |
| S5 | [OpenAI developer guide: Sites](https://learn.chatgpt.com/docs/sites) | Product shape, source linkage, save/deploy separation, storage, identity, sharing and secrets |
| S6 | [OpenAI Help: Creating and managing ChatGPT Sites](https://help.openai.com/en/articles/20001339-creating-and-managing-chatgpt-sites) | Preview, publishing, access, custom domains and product limitations |
| S7 | [OpenAI Help: Managing ChatGPT Sites for your workspace](https://help.openai.com/en/articles/20001338-managing-chatgpt-sites-for-your-workspace) | Workspace access and administrator controls |

S1-S4 are locally installed/current capability contracts. They were read only. No Sites mutation tool was called.

## Capability findings

| Capability | Classification | Evidence and boundary |
|---|---|---|
| Product shape | `CONFIRMED` | S5-S6 describe a hosted builder for websites, interactive web apps and lightweight full-stack experiences. A saved Site is a persistent hosted artifact. |
| Use an existing project | `CONFIRMED` | S1 and S5 describe working from a compatible existing local project linked through `.openai/hosting.json`. Compatibility still requires the Sites build contract. |
| Import arbitrary raw HTML/CSS/JS unchanged | `UNCONFIRMED` | No source promises a zero-adapter import of an arbitrary three-file static directory. Existing-project support is not equivalent to byte-for-byte direct import. |
| Multi-file source project | `CONFIRMED` | S1 and S5 define a source project, build output, server artifact and static assets rather than a single-page-only input. |
| Relative/static assets | `CONFIRMED` | S1's build contract includes static client assets. Exact preservation of Phase 3B root-relative `/assets/*` paths remains build-dependent. |
| Browser JavaScript and `fetch` | `CONFIRMED` | Sites supports interactive web apps (S5-S6); the client runtime is browser JavaScript. This does not confirm any particular remote origin or CORS policy. |
| Same-origin API route | `CONFIRMED` | S1 requires a Cloudflare Worker-compatible server artifact, enabling JS/ESM server routes within the Site application. |
| Cross-origin HTTPS JSON API from browser | `UNCONFIRMED` | No Sites-specific official source found in this audit confirms the full browser-origin, CSP, CORS and account-policy path. This is the Phase 3D experiment target. |
| Sites-managed CORS configuration | `UNCONFIRMED` | No current source documents a Sites CORS control surface. An external API would still need an explicit allowlist. |
| Server-side JavaScript/ESM | `CONFIRMED` | S1 specifies a Cloudflare Worker-compatible ESM server build at `dist/server/index.js`. |
| Native hosted Python process/runtime | `UNSUPPORTED` | The current installed build contract requires a JavaScript/ESM Worker artifact and exposes no Python server entry point. This finding is limited to the current Sites workflow; it is not a claim about unrelated OpenAI products. |
| Separate serverless-function product | `UNCONFIRMED` | A JS server runtime is confirmed; a separate functions product or its lifecycle is not documented by the inspected sources. |
| Server-side outbound HTTPS/proxy | `UNCONFIRMED` | The JS server runtime is confirmed, but the sources inspected do not explicitly confirm outbound egress, destination policy or proxy suitability. |
| Runtime environment variables | `CONFIRMED` | S2, S4 and S5 expose hosted production runtime variables. |
| Secret values | `CONFIRMED` | S2, S4 and S5 expose secret runtime values and explicitly keep them outside prompts, source and `.openai/hosting.json`. |
| D1 structured persistence | `CONFIRMED` | S1-S2 and S5 identify D1 for structured data. |
| R2 object persistence | `CONFIRMED` | S1-S2 and S5 identify R2 for files/blobs. |
| Workspace identity/authentication | `CONFIRMED` | S3-S5 describe workspace identity headers and Sites-managed authentication paths. Trust is limited to the Sites server boundary. |
| Arbitrary external authentication provider | `UNCONFIRMED` | The inspected sources do not confirm a general third-party authentication integration contract. |
| Owner-only/private preview and controlled sharing | `CONFIRMED` | S4-S7 document owner/admin, invited/custom, workspace and public/link access modes, subject to workspace policy. |
| Public deployment | `CONFIRMED` | S4-S6 expose deployment and public/link access. Every deployment URL is described as production, so experiments must not deploy. |
| Custom domain | `CONFIRMED` | S4 and S6 expose custom-domain support, subject to availability, account and administrator policy. |
| Fixed OpenAI-hosted URL | `CONFIRMED` | S4-S6 expose a live/preview or deployment URL. The exact stable hostname pattern is not promised by the evidence. |
| Version history | `CONFIRMED` | S4-S5 separate saved versions from deployments and allow versions to be listed and selected. |
| Rollback by selecting an older saved version | `CONFIRMED` | S4 allows an earlier saved version to be selected for deployment; a one-click UI guarantee is not inferred. |
| Source export/local source linkage | `CONFIRMED` | S4-S5 expose linked source-project/version metadata. A generic UI export format is not separately confirmed. |
| GitHub-native integration | `UNCONFIRMED` | S4 exposes source-repository credentials and commit-based versions, but the repository provider is not guaranteed to be GitHub. |
| Automatic continuous deployment | `UNCONFIRMED` | The confirmed workflow explicitly separates save and deploy. No automatic CD trigger is established. |
| Production-grade business-system suitability | `UNCONFIRMED` | S5-S7 confirm hosting and access controls but also document product/workspace limitations. Load, SLA, compliance and operational requirements require a separate review. |

## Phase 3B compatibility matrix

| Phase 3B component | Result | Reason |
|---|---|---|
| `sites/phase3b-prototype/index.html` | `REQUIRES_THIN_ADAPTER` | Markup can be reused, but it must enter a Sites-compatible project/build structure. |
| `assets/app.css` visual rules | `DIRECTLY_REUSABLE` | No backend or platform dependency was found in the stylesheet. Asset placement may be adapted by the wrapper. |
| `assets/app.js` request/response rendering | `REQUIRES_FRONTEND_CHANGE` | It currently calls same-origin `/api/v1/meihua`; Option A requires a configured external HTTPS endpoint and explicit failure handling. |
| Root-relative `/assets/app.css` and `/assets/app.js` | `REQUIRES_THIN_ADAPTER` | The Sites build must preserve or rewrite these paths deterministically. |
| Same-origin `/api/v1/meihua` assumption | `REQUIRES_EXTERNAL_SERVICE` | The existing handler is the local Python server. Sites cannot host that Python process under the current contract. |
| `scripts/run_sites_phase3b_local_server.py` | `REQUIRES_EXTERNAL_SERVICE` | This loopback `ThreadingHTTPServer` is a development transport, not a Sites runtime artifact. |
| `sites_meihua_service.py` and deterministic Python engine | `REQUIRES_EXTERNAL_SERVICE` | It remains authoritative and unchanged, behind a separately operated HTTPS API if Option A or B is later selected. |
| Contract V1 JSON schemas and status semantics | `DIRECTLY_REUSABLE` | Transport placement does not require a semantic contract change. |
| Client `request_id`, client timestamp and acknowledgements | `DIRECTLY_REUSABLE` | These are browser-side Contract V1 fields and do not depend on the hosting platform. |
| `NarrativeReleaseStatus=UNVERIFIED` gate and no-charge/no-persist semantics | `DIRECTLY_REUSABLE` | They remain application policy; no Phase 3C change is permitted. |
| Current Python-server CSP/security headers | `UNKNOWN` | Sites security-header configuration and exact default CSP are not documented in the inspected evidence. |
| Frontend key handling | `DIRECTLY_REUSABLE` | The frontend contains no API key and must remain keyless. Any future server secret belongs in a server runtime secret store only. |

## Security and privacy boundary

- The browser must never receive an OpenAI key, backend credential or unrestricted service token.
- An external Python API must authenticate requests without trusting client-supplied identity claims and must validate Contract V1 again server-side.
- Allowed browser origins must be explicit; wildcard credentialed CORS is prohibited.
- Rate limiting, request-size limits, timeouts, audit identifiers and safe error envelopes belong at the public API boundary.
- Sites workspace identity headers may be trusted only when delivered to the Sites server runtime as documented by S3; a browser must not synthesize them.
- D1, R2, hosted variables and hosted secrets are not required by the current prototype and must not be provisioned during a capability experiment.
- No real user data, birth data, question history, model prompt, OpenAI response, credential or repository history may enter Phase 3D.
- Data residency, retention, administrator controls and public-link policy require human review before any user-facing deployment.

## Risks and unresolved questions

1. Can a private, non-deployed Sites preview make a browser request to a specifically allowlisted external HTTPS JSON origin?
2. What CSP and connect-source policy applies to that preview, and can it be constrained?
3. Does the Site preview origin remain stable enough for an external API allowlist?
4. Is outbound HTTPS available to the Sites JS server runtime, and what limits apply?
5. Can Phase 3B's exact asset paths be preserved without changing visible behavior?
6. What account/workspace approval is required before even a private capability experiment?

The audit does not infer answers to these questions. The architecture decision therefore remains evidence-gated.
