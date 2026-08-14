# V016 decision log

- V015 semantic matches remain observed evidence, while its live audit verdict remains permanent FAIL/STOP.
- Do not hash or persist the SDK's complete raw response.
- Freeze a reconstructable receipt projection containing response ID, provider model/status, exact usage and the raw structured decision payload digest.
- Keep receipt projection SHA, raw decision SHA and normalized outcome SHA distinct in name and purpose.
- Usage-based cost is a Decimal token-rate reconstruction, not an invoice; absent receipt metadata remains UNKNOWN.
- This stage is 0-live and cannot refill or retroactively repair the V015 ledger.
