# Sites-first Phase 3E private deployment lifecycle result

- Date: `2026-07-13`
- user_consent_obtained: `true`
- Result code: `PRIVATE_DEPLOYMENT_CREATED_OWNER_ACCESS_BLOCKED_BY_EDGE_SECURITY`
- Result scope: `OBSERVED_ACCOUNT_BROWSER_AND_NETWORK_CONTEXT_ON_2026_07_13`
- site_record_created: `true`
- initial_template_required_modification_before_checkpoint: `true`
- synthetic_minimal_page_created: `true`
- checkpoint_count: `1`
- deployment_count: `1`
- production_url_created: `true`
- access_scope: `ONLY_YOU_OWNER_AND_WORKSPACE_ADMINS`
- public_access_created: `false`
- workspace_wide_access_created: `false`
- sharing_created: `false`
- users_or_groups_invited: `false`
- external_requests_configured: `false`
- fetch_configured: `false`
- external_assets_configured: `false`
- database_created: `false`
- D1_created: `false`
- R2_created: `false`
- file_storage_created: `false`
- environment_variables_created: `false`
- secrets_created: `false`
- github_repository_imported: `false`
- owner_access_attempts: `1`
- owner_access_result: `BLOCKED_BY_EDGE_SECURITY`
- observed_block_page_category: `CHATGPT_SITE_EDGE_ACCESS_BLOCK`
- block_trigger_cause: `UNDETERMINED`
- site_content_rendered: `false`
- local_button_test_attempts: `0`
- public_user_access_tested: `false`
- retry_attempts: `0`
- bypass_attempts: `0`
- site_permanently_deleted: `true`
- sites_remaining_after_cleanup: `0`
- cleanup_status: `COMPLETE`
- user_data_transmitted: `false`
- repository_content_transmitted: `false`
- secrets_transmitted: `false`
- OpenAI_Responses_API_calls: `0`
- NarrativeReleaseStatus: `UNVERIFIED`
- should_charge: `false`
- formal_report_persistence_allowed: `false`
- closed_beta_allowed: `false`
- architecture_decision_after_experiment: `D. INSUFFICIENT_EVIDENCE_TO_SELECT`

The observed ChatGPT Sites workflow successfully created one synthetic minimal
Site, one checkpoint and one private production deployment. Access remained
restricted to the owner and workspace administrators. No public, workspace-wide,
shared or invited-user access was created.

The synthetic page did not contain external requests, external assets, storage,
environment variables, secrets, user data or repository content.

The owner made one access attempt through the production Site URL. Before the
Site content rendered, the request was blocked by a `chatgpt.site` edge security
page. The exact cause of the block was not determined. No conclusion is made
about VPN use, geographic location, browser extensions, account state or network
reputation.

No refresh, retry, permission expansion or bypass attempt was made. The page
button was not tested because the Site content never rendered.

The Site and its deployment were permanently deleted through the supported Sites
settings interface. Final cleanup verification showed zero remaining Site
records.

This experiment confirms that checkpoint creation, private deployment and
permanent deletion were available in the observed interface context. It does
not confirm successful owner access to deployed Site content and does not
establish production suitability.

Architecture Option A or B is not selected. The architecture decision remains
`D. INSUFFICIENT_EVIDENCE_TO_SELECT`.
