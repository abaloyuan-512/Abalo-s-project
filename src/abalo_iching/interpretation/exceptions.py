"""Safe exceptions for interpretation providers and validation."""


class InterpretationError(Exception):
    """Base exception that must never contain a key or a complete user question."""


class KnowledgeIntegrityError(InterpretationError):
    pass


class InterpretationValidationError(InterpretationError):
    def __init__(
        self,
        errors: list[str],
        *,
        attempts: int = 1,
        provider_attempts: tuple[dict[str, int | str | None], ...] = (),
    ) -> None:
        self.errors = tuple(errors)
        self.attempts = attempts
        self.provider_attempts = provider_attempts
        self.should_charge = False
        self.persist_as_formal_report_allowed = False
        self.status = "FAILED_VALIDATION"
        super().__init__(f"Interpretation validation failed after {attempts} attempt(s): {'; '.join(errors)}")


class ProviderError(InterpretationError):
    should_charge = False


class ProviderConfigurationError(ProviderError):
    pass


class ProviderRefusalError(ProviderError):
    pass


class ProviderIncompleteError(ProviderError):
    pass


class ProviderSchemaError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderConnectionError(ProviderError):
    pass
