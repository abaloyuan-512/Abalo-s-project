# V015 decision log

- The adapter is necessary only because V014 cannot produce Router outcomes and no trusted producer exists in the current product path.
- Keep the adapter outside V014. Exchange only canonical JSON data.
- Router input is exactly the normalized original question plus one typed critical ambiguity.
- The adapter never performs that normalization on behalf of a caller: input that would change under canonical question validation is rejected at zero provider attempts.
- The model may select only `PASS` or `ASK_ONCE`; only the adapter may mechanically emit `FAILED`, and V014 owns the fixed clarification prompt.
- No live call is required to prove isolation, schema, fail-open behavior, or one-attempt accounting.
- A future Router-only semantic canary needs separate numeric authorization even though the account balance is sufficient.
