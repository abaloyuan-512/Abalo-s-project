# V019 decision log

- V018 live remains permanently FAIL_STOP/TERMINAL_UNKNOWN; V019 does not reinterpret it.
- Classify only exact trusted OpenAI exception types and one internal parse/schema marker.
- Use only frozen codes and stages; never inspect exception attributes, messages or text.
- Boundary stage, not the classifier, determines whether a call may have been sent.
- This is zero-live preparation for a later independently ledgered canary under standing authorization.
