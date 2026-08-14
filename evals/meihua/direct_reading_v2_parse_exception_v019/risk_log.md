# V019 risk log

- Over-specific attribution: controlled by exact-type mapping and UNKNOWN fallback.
- Sensitive exception leakage: controlled by constant-only output and no attribute/message access.
- Classification confused with retry permission: all in-boundary failures remain TERMINAL_UNKNOWN and retries remain zero.
- History rewrite: V018 ledger and outcomes are immutable authority evidence.
