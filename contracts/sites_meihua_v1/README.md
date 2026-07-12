# SITES_MEIHUA_API_CONTRACT_V1

This versioned contract connects a future Sites frontend to the authoritative
Python Meihua engine. The client submits one question and exactly three integers
from 1 through 999. It must not submit calculated charts, Evidence, or program
conclusions. `client_timestamp` is retained only for audit and never determines
chart facts.

The response separates deterministic results, unavailable AI Narrative,
release gates, safe audit metadata, and stable errors. It never exposes API
keys, prompts, local paths, Git identity, or raw internal Evidence objects.

No HTTP transport is selected in Phase 3A. A later HTTPS adapter must preserve
these request and response shapes and delegate all calculation to
`process_sites_meihua_request`.
