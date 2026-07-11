# Meihua OpenAI Adapter V1

## API contract

The optional live adapter uses the OpenAI Python SDK Responses API through
`client.responses.parse` with `AINarrativeContent` as the Pydantic text format.
The model generates only four narrative claim lists. Provider,
response ID, token, latency, and timezone metadata are attached by the service
after validation in the outer `MeihuaInterpretation`. It always sends
`store=False` and `tools=[]`. The default model is
`gpt-5.6-terra`; only `ABALO_OPENAI_MODEL` may override it.

`max_output_tokens` is always sent explicitly. It defaults to 2000 and may be
overridden only through internal `ABALO_OPENAI_MAX_OUTPUT_TOKENS`; values must
be integers in the inclusive 500–4000 range. Invalid configuration fails before
the API call. Responses incomplete because of output-token limits map to
`ProviderIncompleteError` like other incomplete responses.

The API key is read only by the SDK from `OPENAI_API_KEY`. The project does not
accept a key as a request field, does not write a key to disk, and must not log
the key, its length, or a complete user question.

## Failure mapping

Timeout, rate limit, authentication, connection, refusal, incomplete response,
and schema failures map to typed local exceptions. SDK transport retry is
finite (`max_retries=1` by default). The service separately allows exactly one
repair after local semantic validation failure.

The provider protocol returns parsed output, response ID, model, input/output/
total tokens, latency, attempt number, provider name, and prompt version. No
dollar cost is hard-coded. These safe fields may be retained for validation
audit; request text, response free text, and credentials are not logged.

Tests inject a fake client and must never make a real network call. The live
smoke script requires an explicit `--confirm-live-call` flag and a pre-existing
environment key; it must not prompt for or save credentials.

`LIVE_MODEL_AVAILABILITY_NOT_VERIFIED`: Phase 2A performs no live call. The
configured default model must be rechecked against the official model list or
API immediately before an explicitly authorized live smoke test. Mock success
does not establish live model availability.

## Official API references

- Structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Responses migration and storage controls: https://developers.openai.com/api/docs/guides/migrate-to-responses
