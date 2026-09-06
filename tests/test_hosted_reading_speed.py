from __future__ import annotations

import threading
import time

import pytest

from tests.test_hosted_api import ENGINE_KEY, hosted_api, request, running_server, valid_direct_reading_request
from tests.test_sites_direct_reading_v2 import _complete_text
from tests.test_sites_direct_reading_v3_p9 import FINALE, Provider
from abalo_iching.application.sites_direct_reading_speed_v1 import PROMPT_SUFFIX, READING_PROFILE
from abalo_iching.application.sites_direct_reading_v3 import process_prepared_direct_reading_v2_request


@pytest.mark.parametrize("profile,effort,verbosity", [(None, "high", "standard"),
                                                      (READING_PROFILE, "medium", "concise")])
def test_opt_in_profile_end_to_end_preserves_defaults_and_idempotency(monkeypatch, profile, effort, verbosity) -> None:
    monkeypatch.setenv("ABALO_DIRECT_READING_V2_ENABLED", "true")
    monkeypatch.delenv("ABALO_DIRECT_READING_REASONING_EFFORT", raising=False)
    prepared_requests = []
    provider_configs = []
    ready = threading.Event()
    release = threading.Event()

    def provider(**kwargs):
        provider_configs.append(kwargs)
        return Provider(_complete_text().replace("## 六三", "## 动爻：六三") + FINALE)

    def process(prepared, **kwargs):
        prepared_requests.append(prepared)
        ready.set()
        release.wait(timeout=5)
        return process_prepared_direct_reading_v2_request(prepared, **kwargs)

    monkeypatch.setattr(hosted_api, "OpenAIDirectReadingProvider", provider)
    monkeypatch.setattr(hosted_api, "process_prepared_direct_reading_v2_request", process)
    payload = valid_direct_reading_request()
    if profile:
        payload["reading_profile"] = profile
    with running_server() as port:
        assert READING_PROFILE in request(port, "GET", "/healthz")[2]["direct_reading_profiles"]
        status, _, pending = request(port, "POST", "/api/preview/v2/direct-reading/jobs", key=ENGINE_KEY, payload=payload)
        assert status == 202
        assert pending["chart_facts"]
        assert ready.wait(2)
        for _ in range(3):
            assert request(port, "POST", "/api/preview/v2/direct-reading/jobs", key=ENGINE_KEY, payload=payload)[0] == 202
        changed = {**payload, "reading_profile": "standard" if profile else READING_PROFILE}
        assert request(port, "POST", "/api/preview/v2/direct-reading/jobs", key=ENGINE_KEY, payload=changed)[0] == 409
        release.set()
        final = pending
        for _ in range(100):
            status, _, final = request(port, "GET", "/api/preview/v2/direct-reading/jobs/" + str(payload["request_id"]), key=ENGINE_KEY)
            if status == 200:
                break
            time.sleep(.02)
        assert final["status"] == "SUCCESS"
        assert final["product_presentation"]
    assert len(prepared_requests) == 1
    assert provider_configs == [{"reasoning_effort": effort, "output_profile": verbosity}]
    assert prepared_requests[0].prompt_version.endswith(PROMPT_SUFFIX) == bool(profile)


@pytest.mark.parametrize("profile", ["unknown", {}, None, []])
def test_invalid_profile_rejected_before_preparation(monkeypatch, profile) -> None:
    monkeypatch.setenv("ABALO_DIRECT_READING_V2_ENABLED", "true")
    monkeypatch.setattr(hosted_api, "prepare_direct_reading_v2_request", lambda *a, **kw: pytest.fail("must not prepare"))
    with running_server() as port:
        status, _, body = request(port, "POST", "/api/preview/v2/direct-reading/jobs", key=ENGINE_KEY,
                                  payload={**valid_direct_reading_request(), "reading_profile": profile})
    assert status == 400
    assert body["status"] == "invalid_reading_profile"
