"""Domain-specific exceptions with stable public meanings."""


class MeihuaError(Exception):
    """Base class for deterministic engine failures."""


class InputValidationError(MeihuaError, ValueError):
    """Raised when chart input violates the frozen input contract."""


class DataIntegrityError(MeihuaError):
    """Raised when versioned static data is missing or inconsistent."""


class CalendarCalculationError(MeihuaError):
    """Raised when an exact solar-term/month calculation cannot be produced."""
