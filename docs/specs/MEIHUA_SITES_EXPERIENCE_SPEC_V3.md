# Meihua Sites Experience Spec V3

## Scope

This specification versions the question-aligned presentation layer used by
Sites Contract V3.  It does not modify `MEIHUA_RULE_SPEC_V1`, the deterministic
casting algorithm, or any serialized chart fact.

## Input boundary

- The user provides a concrete question of 6–160 normalized characters.
- `question_domain`, `decision_goal`, `time_horizon`, `decision_stage`, and
  `key_uncertainty` are finite presentation context.
- Only the three integers and authoritative server time enter `MeihuaInput`.
- Free text is echoed to anchor the report. It is never parsed as chart evidence
  and never changes a chart, conclusion level, date, motive, or predicted event.

## Question alignment

`SITES_CLARITY_REPORT_V3` must:

1. Repeat the exact user question before any interpretation.
2. Name the selected domain subject in the directional answer.
3. Use domain-specific, observable reality checks.
4. Use the selected goal, stage, uncertainty, and horizon only to choose a
   reversible next action and explanatory emphasis.
5. Keep rule reasoning in a separate evidence section.
6. State visibly that reality context is not hexagram evidence.

## Result order

1. Exact question.
2. One direct, domain-aligned directional answer.
3. What the direction means.
4. Three observable reality checks.
5. One smallest reversible next action.
6. Three pause signals.
7. Base, mutual, and changed hexagrams plus rule reasoning.
8. Epistemic boundary.

## Language rules

- Prefer plain, observable language over metaphysical abstraction.
- Never claim certainty about another person's mind or a future event.
- Never generate a specific date.
- Favorable readings still require reality checks.
- Unfavorable readings reduce irreversible cost rather than prescribe fatalism.
- Relationship, work, cooperation, and personal-planning language must not leak
  into one another.

## Release boundary

`SITES_CLARITY_REPORT_V3` is deterministic template output. AI Narrative remains
`UNVERIFIED`; charging and formal report persistence remain blocked.
