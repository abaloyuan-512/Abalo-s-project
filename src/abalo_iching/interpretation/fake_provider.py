"""Deterministic provider for tests and explicitly labelled offline demos."""

from __future__ import annotations

from collections.abc import Iterable

from .enums import EpistemicBasis, NarrativeKind, SubjectScope
from .models import (
    AINarrativeClaim,
    AINarrativeContent,
    InterpretationRequest,
    PromptPackage,
    ProviderResult,
    SynthesisResult,
)


def build_conservative_fake_output(
    request: InterpretationRequest,
    synthesis: SynthesisResult,
) -> AINarrativeContent:
    """Create narrative only; it contains no chart restatement, conclusion, or timing."""

    relation_ids = [item.evidence_ids[0] for item in synthesis.relation_assessments]
    action_ids = synthesis.supporting_evidence_ids or synthesis.blocking_evidence_ids or relation_ids
    condition_ids = [item.evidence_ids[0] for item in synthesis.relation_assessments if item.conditions]
    return AINarrativeContent(
        plain_language_explanation=[
            AINarrativeClaim(
                text="这些关系证据提示需要核对相应条件与现实反馈。",
                evidence_ids=relation_ids,
                narrative_kind=NarrativeKind.EXPLANATION,
                subject_scope=SubjectScope.SITUATION,
                epistemic_basis=EpistemicBasis.CHART_EVIDENCE,
            )
        ],
        real_world_advice=[
            AINarrativeClaim(
                text="可以考虑先进行可撤回的小步验证。",
                evidence_ids=action_ids,
                narrative_kind=NarrativeKind.ACTION_OPTION,
                subject_scope=SubjectScope.PROCESS,
                epistemic_basis=EpistemicBasis.ACTION_OPTION,
            )
        ],
        conditions_that_change_outcome=(
            [
                AINarrativeClaim(
                    text="建议验证程序列出的条件是否已经满足。",
                    evidence_ids=condition_ids,
                    narrative_kind=NarrativeKind.CONDITION_TO_VERIFY,
                    subject_scope=SubjectScope.SITUATION,
                    epistemic_basis=EpistemicBasis.UNCERTAINTY,
                )
            ]
            if condition_ids
            else []
        ),
        review_questions=[
            AINarrativeClaim(
                text="你是否已经获得可以核对这些条件的现实反馈？",
                evidence_ids=relation_ids,
                narrative_kind=NarrativeKind.REVIEW_QUESTION,
                subject_scope=SubjectScope.USER,
                epistemic_basis=EpistemicBasis.UNCERTAINTY,
            )
        ],
    )


class FakeInterpretationProvider:
    def __init__(self, outputs: Iterable[AINarrativeContent | dict[str, object] | Exception]) -> None:
        self._outputs = list(outputs)
        self.call_count = 0
        self.attempt_numbers: list[int] = []

    def generate(self, prompt: PromptPackage, *, attempt_number: int) -> ProviderResult:
        self.call_count += 1
        self.attempt_numbers.append(attempt_number)
        if not self._outputs:
            raise RuntimeError("Fake provider has no configured output")
        item = self._outputs.pop(0)
        if isinstance(item, Exception):
            raise item
        return ProviderResult(
            parsed_output=item,
            response_id=f"fake-response-{self.call_count}",
            model="fake-structured-model",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            latency_ms=0,
            attempt_number=attempt_number,
            provider_name="FAKE",
            prompt_version=prompt.prompt_version,
        )
