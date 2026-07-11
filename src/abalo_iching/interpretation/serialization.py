"""Stable JSON helpers for validated interpretation artifacts."""

from .models import AINarrativeContent, MeihuaInterpretation, ServiceResult


def interpretation_content_to_json(value: AINarrativeContent, *, indent: int | None = 2) -> str:
    return value.model_dump_json(indent=indent)


def interpretation_content_from_json(payload: str) -> AINarrativeContent:
    return AINarrativeContent.model_validate_json(payload)


def interpretation_to_json(value: MeihuaInterpretation, *, indent: int | None = 2) -> str:
    return value.model_dump_json(indent=indent)


def interpretation_from_json(payload: str) -> MeihuaInterpretation:
    return MeihuaInterpretation.model_validate_json(payload)


def service_result_to_json(value: ServiceResult, *, indent: int | None = 2) -> str:
    return value.model_dump_json(indent=indent)


def service_result_from_json(payload: str) -> ServiceResult:
    return ServiceResult.model_validate_json(payload)
