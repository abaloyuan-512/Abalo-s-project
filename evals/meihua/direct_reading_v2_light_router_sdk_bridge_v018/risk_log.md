# V018 risk log

- Risk: fixture-private lineage being required by a real SDK response. Control: a real exact SDK response receives a bridge-local correlation token at first snapshot; fixture stamps only exercise mixed-source rejection.
- Risk: consuming a response for an invalid request. Control: request validation precedes the one-shot SDK snapshot.
- Risk: treating fixture counts as provider calls. Control: separate SDK extraction and V017 fixture counters; live and real-provider counts remain zero.
- Risk: duplicating receipt hashing. Control: success is accepted only when the unchanged V017 audit and rebuild function match.
- Risk: scope creep into the Router, high or product. Control: module imports no OpenAI client, high, cast or V014 consumer.
