# Meihua Sites Experience Spec V2

## Scope

This specification versions the product interpretation layer used by Sites
Contract V3. It does not modify `MEIHUA_RULE_SPEC_V1` or any deterministic
casting algorithm.

## Input boundary

- The user must provide a concrete question of 6–160 normalized characters.
- `question_text`, `decision_stage`, and `key_uncertainty` are presentation
  context only.
- Only the three integers and the authoritative server time enter
  `MeihuaInput`.
- Free text must never be parsed as chart evidence or used to invent facts,
  motives, dates, or outcomes.

## Result order

The result page must present information in this order:

1. The exact question the user asked.
2. One plain-language directional answer.
3. What that answer means and the current priority.
4. Three observable continue signals and three observable pause signals.
5. One smallest reversible next action.
6. Base, mutual, changed hexagrams and rule reasoning as supporting evidence.
7. A visible epistemic boundary.

## Language rules

- Prefer actionable, observable language over metaphysical abstraction.
- Never claim certainty about another person's mind or a future event.
- Never produce a specific date.
- A favorable reading still requires real-world verification.
- An unfavorable reading recommends reducing irreversible cost, not fatalism.

## Release boundary

`SITES_CLARITY_REPORT_V2` is deterministic template output. AI Narrative remains
`UNVERIFIED`, so charging, formal persistence, and closed beta remain blocked.
