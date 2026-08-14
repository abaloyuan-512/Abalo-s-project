# V017 risk log

- Risk: treating a caller-provided token as provenance. Control: token is issued inside the exact fixture response type and cannot be passed to the processor.
- Risk: mixing fields from two individually valid receipts. Control: each field is sealed with one instance token and mixed-token extraction fails without evidence release.
- Risk: reusing an old receipt in another case. Control: one-shot consumption plus request-binding SHA; second use releases no ID, usage or digest.
- Risk: claiming fixture evidence proves a real provider call. Control: all evidence says FIXTURE, live calls and real provider are zero.
- Risk: broad infrastructure or product drift. Control: no changes to V015/V016, V014/high/engine/product paths.
