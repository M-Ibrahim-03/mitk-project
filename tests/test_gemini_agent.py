from types import SimpleNamespace

import pytest

from veil.gemini_agent import (
    AgentConfigurationError,
    AgentProtocolError,
    GeminiAgent,
    create_gemini_client,
    resolve_agent_mode,
)


class RecordingModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class RecordingClient:
    def __init__(self, responses):
        self.models = RecordingModels(responses)


def test_gemini_agent_returns_validated_tool_proposal_without_executing_it() -> None:
    protected_message = (
        "Check ticket TICKET-DEMO-1042 for [[EMAIL:V0123456789]]."
    )
    function_call = SimpleNamespace(
        name="lookup_helpdesk_ticket",
        args={
            "ticket_id": "TICKET-DEMO-1042",
            "user_message": protected_message,
            "question": "status and next update",
        },
    )
    client = RecordingClient([SimpleNamespace(function_calls=[function_call])])

    proposal = GeminiAgent(client).prepare_tool_call(protected_message)

    assert proposal.tool_name == "lookup_helpdesk_ticket"
    assert proposal.payload["ticket_id"] == "TICKET-DEMO-1042"
    assert len(client.models.calls) == 1
    request = client.models.calls[0]
    assert request["contents"] == protected_message
    assert "riley@example.test" not in str(request)
    assert request["config"]["automatic_function_calling"]["disable"] is True
    assert request["config"]["tool_config"]["function_calling_config"][
        "allowed_function_names"
    ] == ["lookup_helpdesk_ticket"]


def test_gemini_agent_rejects_unknown_or_malformed_tool_calls() -> None:
    unknown = SimpleNamespace(name="send_email", args={"to": "safe"})
    client = RecordingClient([SimpleNamespace(function_calls=[unknown])])

    with pytest.raises(AgentProtocolError):
        GeminiAgent(client).prepare_tool_call("Synthetic tokenized request")


def test_gemini_agent_rejects_support_intake_for_ticket_only_flow() -> None:
    call = SimpleNamespace(
        name="submit_support_request",
        args={"user_message": "Synthetic ticket request", "question": "help"},
    )
    client = RecordingClient([SimpleNamespace(function_calls=[call])])

    with pytest.raises(AgentProtocolError):
        GeminiAgent(client).prepare_tool_call("Synthetic ticket request")


def test_gemini_agent_requires_one_tool_call() -> None:
    client = RecordingClient([SimpleNamespace(function_calls=[])])

    with pytest.raises(AgentProtocolError):
        GeminiAgent(client).prepare_tool_call("Synthetic tokenized request")


def test_gemini_agent_rejects_changed_or_extra_tool_arguments() -> None:
    changed = SimpleNamespace(
        name="submit_support_request",
        args={"user_message": "Changed request", "question": "help"},
    )
    client = RecordingClient([SimpleNamespace(function_calls=[changed])])
    with pytest.raises(AgentProtocolError):
        GeminiAgent(client).prepare_tool_call("Original tokenized request")


def test_gemini_agent_rejects_ticket_ids_not_in_the_protected_request() -> None:
    call = SimpleNamespace(
        name="lookup_helpdesk_ticket",
        args={
            "ticket_id": "TICKET-DEMO-9999",
            "user_message": "Please check TICKET-DEMO-1042",
            "question": "status",
        },
    )
    client = RecordingClient([SimpleNamespace(function_calls=[call])])
    with pytest.raises(AgentProtocolError):
        GeminiAgent(client).prepare_tool_call("Please check TICKET-DEMO-1042")


def test_gemini_agent_sanitizes_provider_exception_details() -> None:
    class RaisingModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("prompt contained riley@example.test")

    with pytest.raises(AgentProtocolError, match="Gemini request failed") as error:
        GeminiAgent(SimpleNamespace(models=RaisingModels())).prepare_tool_call(
            "Synthetic tokenized request"
        )
    assert "riley@example.test" not in str(error.value)
    assert "RuntimeError" in str(error.value)

    extra = SimpleNamespace(
        name="submit_support_request",
        args={"user_message": "Original tokenized request", "question": "help", "url": "bad"},
    )
    client = RecordingClient([SimpleNamespace(function_calls=[extra])])
    with pytest.raises(AgentProtocolError):
        GeminiAgent(client).prepare_tool_call("Original tokenized request")


def test_gemini_agent_writes_final_answer_from_protected_tool_result() -> None:
    protected_message = "Check TICKET-DEMO-1042. Contact me at [[EMAIL:V0123456789]]."
    protected_tool_result = {"ticket": {"ticket_id": "TICKET-DEMO-1042", "status": "In progress"}}
    client = RecordingClient([SimpleNamespace(text="TICKET-DEMO-1042 is [[EMAIL:V0123456789]].")])

    answer = GeminiAgent(client).create_final_answer(
        protected_message,
        "lookup_helpdesk_ticket",
        {"ticket_id": "TICKET-DEMO-1042", "user_message": protected_message},
        protected_tool_result,
    )

    assert answer == "TICKET-DEMO-1042 is [[EMAIL:V0123456789]]."
    request = client.models.calls[0]
    assert "riley@example.test" not in request["contents"]
    assert "[[EMAIL:V0123456789]]" in request["contents"]
    assert request["config"].get("tools") is None


def test_agent_mode_requires_server_key_only_when_gemini_is_selected(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("VEIL_AGENT_MODE", "deterministic")
    assert resolve_agent_mode() == "deterministic"

    monkeypatch.setenv("VEIL_AGENT_MODE", "gemini")
    with pytest.raises(AgentConfigurationError):
        resolve_agent_mode()

    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-test-key")
    assert resolve_agent_mode() == "gemini"


def test_gemini_client_retries_transient_provider_server_errors(monkeypatch) -> None:
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-test-key")
    captured: dict[str, object] = {}
    client = object()

    def fake_client(**kwargs):
        captured.update(kwargs)
        return client

    monkeypatch.setattr(genai, "Client", fake_client)

    assert create_gemini_client() is client
    http_options = captured["http_options"]
    assert isinstance(http_options, dict)
    retry_options = http_options["retry_options"]
    assert retry_options == {
        "attempts": 3,
        "initial_delay": 0.5,
        "max_delay": 2.0,
        "jitter": 0.25,
    }
