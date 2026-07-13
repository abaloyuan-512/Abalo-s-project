# Sites-first Phase 3D capability experiment result

- Date: `2026-07-13`
- Phase 3C baseline: `D. INSUFFICIENT_EVIDENCE_TO_SELECT`
- User authorization obtained: `true`
- Result code: `BLOCKED_REQUIRES_PRODUCTION_DEPLOYMENT`
- Result scope: `OBSERVED_ACCOUNT_AND_INTERFACE_CONTEXT_ON_2026_07_13`
- private_site_records_created: `2`
- internal_preview_reported_by_sites: `true`
- user_openable_private_preview_confirmed: `false`
- checkpoint_created: `false`
- sites_deployment_created: `false`
- public_access_created: `false`
- sharing_created: `false`
- users_invited: `false`
- synthetic_post_attempts: `0`
- preflight_observed: `false`
- preflight_status: `NOT_ATTEMPTED`
- post_status: `NOT_ATTEMPTED`
- javascript_read_response: `false`
- response_shape_match: `false`
- CSP_result: `NOT_OBSERVED`
- CORS_result: `NOT_OBSERVED`
- network_result: `NOT_ATTEMPTED_BLOCKED_BY_SITES_DEPLOYMENT_REQUIREMENT`
- observed_sites_constraint: `USER_REVIEWABLE_CHECKPOINT_WOULD_START_PRIVATE_PRODUCTION_DEPLOYMENT`
- cloudflare_worker_created: `true`
- cloudflare_worker_temporarily_deployed: `true`
- cloudflare_worker_non_synthetic_get_observed: `true`
- non_synthetic_get_source: `UNDETERMINED_PLATFORM_OR_INTERFACE_ACTIVITY`
- endpoint_provider: `CLOUDFLARE_WORKER`
- observability_logs_disabled_before_synthetic_post: `true`
- synthetic_request_body_logged: `false`
- endpoint_deleted: `true`
- site_records_deleted: `2`
- sites_remaining_after_cleanup: `0`
- cloudflare_projects_remaining_after_cleanup: `0`
- cleanup_status: `COMPLETE`
- secrets_transmitted: `false`
- user_data_transmitted: `false`
- repository_content_transmitted: `false`
- OpenAI_Responses_API_calls: `0`
- NarrativeReleaseStatus: `UNVERIFIED`
- should_charge: `false`
- formal_report_persistence_allowed: `false`
- closed_beta_allowed: `false`
- architecture_decision_after_experiment: `D. INSUFFICIENT_EVIDENCE_TO_SELECT`

The observed ChatGPT Sites workflow allowed private owner-only Site records to
be created, but did not provide a user-openable review version without creating
a checkpoint. In the observed account and interface context, creating that
checkpoint would automatically start a private production deployment.

Because every Sites deployment was outside the authorized experiment boundary,
the experiment stopped before checkpoint creation, deployment, CORS
configuration or synthetic POST execution.

One temporary Cloudflare Worker had already been created during experiment
preparation. A single non-synthetic GET was observed during setup; its exact
platform or interface source was not determined. No synthetic JSON POST was
sent. Observability logs were disabled before any synthetic request, and the
Worker was permanently deleted.

Both private Site records were permanently deleted. Final cleanup verification
showed zero remaining Sites records and zero remaining Cloudflare Worker
projects.

This result does not select Architecture Option A or B. The architecture
decision remains `D. INSUFFICIENT_EVIDENCE_TO_SELECT`.
