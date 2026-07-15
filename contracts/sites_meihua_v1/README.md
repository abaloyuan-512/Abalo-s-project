# SITES_MEIHUA_API_CONTRACT_V1

This versioned contract connects a future Sites frontend to the authoritative
Python Meihua engine. A client `request_id` must match
`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`; `invalid-request` is reserved for the
server's safe error fallback and is rejected as client input. No trimming or
normalization is performed. The client submits one question and exactly three integers
from 1 through 999. It must not submit calculated charts, Evidence, or program
conclusions. `client_timestamp` is retained only for audit and never determines
chart facts. It must use the RFC3339 subset
`YYYY-MM-DDTHH:MM:SS[.fraction](Z|±HH:MM)`.

The response separates deterministic results, unavailable AI Narrative,
release gates, safe audit metadata, and stable errors. It never exposes API
keys, prompts, local paths, Git identity, or raw internal Evidence objects.

No HTTP transport is selected in Phase 3A. A later HTTPS adapter must preserve
these request and response shapes and delegate all calculation to
`process_sites_meihua_request`.

The Phase 3G P0 input guard adds four error codes to the V1 allowlist:
`UNSUPPORTED_PREDICTION_REQUEST`, `UNSUPPORTED_THIRD_PARTY_INFERENCE`,
`UNSUPPORTED_HIGH_RISK_REQUEST`, and `IMMEDIATE_SAFETY_RISK`. This is an
additive error-code patch only. The contract version, request schema, response
envelope, success response, and endpoint remain unchanged.
