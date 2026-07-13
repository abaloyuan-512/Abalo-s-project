# Sites-first Phase 3B local prototype

## Frozen topology

```text
Browser page
  -> same-origin POST /api/v1/meihua
  -> loopback-only HTTP adapter
  -> process_sites_meihua_request
  -> authoritative deterministic Python engine
  -> SITES_MEIHUA_API_CONTRACT_V1 response
  -> safe browser presentation
```

The HTTP adapter is transport only. It contains no chart calculation, business
rules, Narrative generation, Evidence construction, persistence, database
access, provider integration, or external network call. It does not read
`OPENAI_API_KEY`. The browser never submits derived chart facts, Evidence, or a
deterministic conclusion.

The server accepts only the literal host `127.0.0.1`, defaults to port `8765`,
uses a fixed route allowlist, caps JSON bodies at 16 KiB, and is not a production
server. It rejects `0.0.0.0`, LAN addresses, and public addresses. Static assets
are repository-local and responses carry restrictive CSP, framing, MIME, and
referrer headers. API responses are `no-store`.

## Contract and normalization boundary

Contract V1 continues to limit the raw `question_text` to 1 through 500
characters and reject whitespace-only input. The application validates that
raw length before trimming. Only a valid raw value is normalized. The normalized
question is used by the service, request hash, and success response. Invalid raw
input never reaches `cast_meihua`.

## Privacy and release boundary

There are no accounts, OTPs, cookies, browser storage, analytics, payments, or
history. The adapter does not log question text, full request bodies, or the
association between the three numbers and a question. Safe logs are limited to
request ID, HTTP status, audit ID, latency, and error classification.

AI Narrative is unavailable and visibly `UNVERIFIED`. Charging, formal report
persistence, and closed beta participation remain disabled. The page is a local
prototype only and is not a deployed or published Sites property.
