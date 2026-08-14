# V018 decision log

- V018 is necessary only because V015's real adapter discarded response ID and usage while V017 proved fixture receipt telemetry separately.
- Add one exact OpenAI `ParsedResponse[ModelDecision]` bridge; do not change V015 or V017.
- Validate the request before consuming the SDK response; snapshot one SDK instance once and hand one sealed payload to V017.
- A local SDK-instance SHA is an audit correlation value, not a provider signature or invoice.
- No OpenAI client, environment-key access, live call, high call or product integration exists in this stage.
