# Sites Phase 3A Engine Reuse Audit

Baseline: `853fb299fdc6e4006fbce02b09439cfd31b12103` on
`v3/sites-first-phase3a`.

## Directly reusable

| Capability | Authoritative entry | Existing output |
| --- | --- | --- |
| Three-number cast | `abalo_iching.meihua.cast_meihua(MeihuaInput)` | Immutable `MeihuaChart` |
| Input contract | `validate_cast_numbers` | Three non-boolean integers, each 1–999 |
| Base, mutual, changed hexagrams and moving line | `MeihuaChart` | Versioned hexagram objects and line 1–6 |
| Body/use and five elements | `MeihuaChart.body_use_assignment` and relations | Trigrams, elements and relation enums |
| Seasonal strength | `MeihuaChart.season_context` | Body/initial-use/changed-use strength |
| Deterministic conclusion | `ConclusionSynthesizer.synthesize` | Strict `SynthesisResult` |
| Knowledge boundary | `KnowledgeAccessPolicy` and `select_knowledge` | Production mode permits APPROVED only |
| Release gate | `narrative_release_snapshot` | `UNVERIFIED` repository-controlled snapshot |
| Serialization | `chart_to_dict`, Pydantic `model_dump(mode="json")` | Stable internal serialization primitives |

`cast_meihua` remains the sole casting authority. The Phase 3A service delegates
to it and does not reproduce modulus, trigram, hexagram, body/use, calendar,
seasonal-strength, Evidence, or conclusion rules.

## Needs a lightweight wrapper

- Reject frontend-derived chart, Evidence, and conclusion fields.
- Convert safe authoritative results into Contract V1 without exposing raw
  internal Evidence or internal paths.
- Keep the client timestamp as audit metadata only; the Python service clock is
  the calculation time source.
- Apply the frozen Narrative and release-gate response.
- Add transport-neutral JSON input/output and local static HTML rendering.

The framework-independent wrapper is
`abalo_iching.application.sites_meihua_service.process_sites_meihua_request`.
The repository currently has no FastAPI, Flask, Django, Starlette, or other HTTP
framework dependency, so Phase 3A does not add one.

## Deferred in Phase 3A

- HTTPS transport, deployment, hosted persistence, authentication integration,
  quota enforcement, production observability, and Sites runtime adaptation.
- Real AI Narrative and CASE-007 V5 live validation.
- Real-user report publication and formal storage.

## Forbidden in the frontend

The frontend must not calculate hexagrams, moving lines, body/use, elements,
seasonal strength, deterministic conclusions, Evidence, charging eligibility,
or release status. It must not store secrets, call a model directly, or present
Mock Narrative as a real result.
