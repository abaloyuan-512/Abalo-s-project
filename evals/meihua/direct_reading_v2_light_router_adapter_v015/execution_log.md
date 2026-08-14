# V015 execution log

- Reused the previously approved existing `OPENAI_API_KEY`; presence was checked without revealing the secret.
- Added one isolated adapter and focused fixture tests.
- No live provider was instantiated; no network request was sent.
- Initial focused run exposed one test assertion typo; the test alone was corrected before candidate freeze.
- PMO found pre-freeze that normalization could make the SHA audit overclaim byte preservation; the adapter now rejects non-canonical question input without attempting the provider.
- PMO found pre-freeze that fixture receipts could self-declare `FAILED`; raw provider schema is now limited to PASS/ASK_ONCE and all FAILED outcomes are adapter-generated.
