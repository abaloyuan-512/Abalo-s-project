# V021 decision log

- V020 remains permanently FAIL; V021 only validates exact trusted 400/5xx status consistency.
- Status is read once only after exact BadRequest/InternalServer type gates; every conflict is UNKNOWN.
