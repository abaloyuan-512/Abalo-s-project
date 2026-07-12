# Sites-first Phase 3A Architecture

Status: `SITES_PHASE_3A_STATUS=ALLOWED_WITH_RELEASE_RESTRICTIONS`.

## Responsibility boundary

### Sites or future web frontend

Owns presentation, question and three-number input, user confirmation, loading
and error states, report display, explicit `UNVERIFIED` display, and invocation
of the backend contract. It stores no key and performs no deterministic
calculation.

### Authoritative Python service

Owns input validation, casting, base/mutual/changed hexagrams, moving line,
body/use, elements, seasonal strength, deterministic conclusions, safe Evidence
summary, release gates, charge and persistence decisions, and audit fields.

### AI Narrative in the minimum loop

No AI provider is called. Narrative is fixed to `UNVERIFIED`, `available=false`,
and `content=null`. `should_charge=false`,
`formal_report_persistence_allowed=false`, and `closed_beta_allowed=false`.
The frontend must state “解释功能尚未完成真实路径验证” and must not substitute
a Mock Narrative.

## Hosting-compatible topology

The architecture does not assume that Sites can run Python directly. Contract
V1 supports both later topologies:

1. a Sites frontend calls an independently deployed Python HTTPS API; or
2. after suitable Sites server capability is confirmed, a thin Sites adapter
   forwards Contract V1 to the same Python application service.

Neither topology may duplicate the Python core engine or change Contract V1
semantics. Phase 3A adds no HTTP dependency, deployment, or public site.

## Data flow

```text
Future frontend
  -> SITES_MEIHUA_API_CONTRACT_V1 request
  -> framework-independent Python application service
  -> existing cast_meihua + production KnowledgeAccessPolicy + ConclusionSynthesizer
  -> frozen NarrativeReleaseSnapshot
  -> frontend-safe SITES_MEIHUA_API_CONTRACT_V1 response
```

The client timestamp is audit-only. Client-computed charts, Evidence, and
conclusions are rejected. Raw internal Evidence, prompts, keys, local paths,
Git identity, and stack traces never cross the frontend boundary.

## Frozen release restrictions

Until the V5 live path is independently validated and approved, there is no
charging, formal Narrative persistence, closed beta, real-user AI report
publication, or weakening of Phase 2C release gates. Python remains the only
authoritative deterministic source.
