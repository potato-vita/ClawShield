import pytest
from pydantic import ValidationError

from traceshield_method.runtime_schemas import RuntimeParams, RuntimeRequest


def test_runtime_request_requires_positive_step() -> None:
    with pytest.raises(ValidationError):
        RuntimeParams.model_validate(
            {
                "session_id": "s",
                "run_id": "r",
                "trace_id": "t",
                "current_step_seq": 0,
                "intent_frame": {},
                "events": [],
            }
        )


def test_health_request_needs_no_params() -> None:
    request = RuntimeRequest.model_validate(
        {"protocol_version": "v1", "request_id": "health-1", "method": "health"}
    )
    assert request.params is None
