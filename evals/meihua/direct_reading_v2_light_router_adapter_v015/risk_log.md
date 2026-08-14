# V015 risk log

- Treating account balance as call-count authorization: controlled by holding live calls at zero.
- Letting Router see numbers, chart or optional context: controlled by strict request schema and AST tests.
- Free-form model output or question rewriting: controlled by strict enum schema and extra-field rejection.
- Retry or second model attempt: controlled by `max_retries=0`, single-use real adapter, and fixture counters.
- Leaking raw question/provider body/exception detail in audit: controlled by SHA-only audit fields.
- Fixture evidence being mislabeled as real model quality: final verdict remains offline-only.
