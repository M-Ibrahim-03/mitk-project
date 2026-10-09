"""Streamlit entry point for the local, event-backed Veil judging workflow."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from veil.demo_agent import (
    DEMO_REQUESTER,
    DEMO_USER_REQUEST,
    AgentRequest,
    RequesterDetails,
)
from veil.demo_flow import WorkflowEvent, run_ticket_demo


STAGE_DEFINITIONS = (
    ("agent", "1. Agent prepares the helpdesk request"),
    ("veil", "2. Veil checks and protects the request"),
    ("helpdesk", "3. Helpdesk receives the protected request"),
    ("restore", "4. Veil restores the reply"),
)

STAGE_STYLE = """
<style>
.veil-flow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
  margin: 0.5rem 0 1rem;
}
.veil-stage {
  min-height: 8.5rem;
  padding: 1rem;
  border: 1px solid #344054;
  border-radius: 18px;
  background: linear-gradient(145deg, #111827, #1d2939);
  color: #f2f4f7;
  transition: transform 240ms ease, border-color 240ms ease, box-shadow 240ms ease;
}
.veil-stage:hover { transform: translateY(-3px); }
.veil-stage.veil-complete {
  border-color: #32d583;
  background: linear-gradient(145deg, #062c25, #123b34);
}
.veil-stage.veil-active {
  border-color: #84adff;
  background: linear-gradient(145deg, #172554, #312e81);
  animation: veilPulse 1.35s ease-in-out infinite;
}
.veil-stage.veil-blocked {
  border-color: #f97066;
  background: linear-gradient(145deg, #3b111b, #571b24);
}
.veil-stage.veil-failed {
  border-color: #fdb022;
  background: linear-gradient(145deg, #3b250b, #573613);
}
.veil-stage-number {
  color: #b2ccff;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.veil-stage-title { display: block; margin: 0.5rem 0; font-weight: 700; }
.veil-stage-status { color: #d0d5dd; font-size: 0.9rem; }
@keyframes veilPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(132, 173, 255, 0.16); }
  50% { box-shadow: 0 0 0 7px rgba(132, 173, 255, 0.28); }
}
@media (prefers-reduced-motion: reduce) {
  .veil-stage, .veil-stage:hover { animation: none; transition: none; transform: none; }
}
@media (max-width: 800px) {
  .veil-flow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .veil-flow { grid-template-columns: 1fr; }
}
</style>
"""


def _clear_trace() -> None:
    st.session_state.pop("veil_ticket_demo", None)


def _reset_form() -> None:
    st.session_state["veil_message"] = DEMO_USER_REQUEST
    st.session_state["veil_name"] = DEMO_REQUESTER["name"]
    st.session_state["veil_email"] = DEMO_REQUESTER["email"]
    st.session_state["veil_phone"] = DEMO_REQUESTER["phone"]
    st.session_state["veil_custom_sensitive_values"] = ""
    _clear_trace()


def _event_state(event: WorkflowEvent, state: dict[str, str]) -> None:
    if event.stage in {"request_received", "agent_planning", "tool_call_prepared"}:
        state["agent"] = "complete" if event.status == "complete" else event.status
    elif event.stage in {"privacy_scan", "egress_gate"}:
        state["veil"] = event.status
        if event.stage == "egress_gate" and event.status == "complete":
            state["veil"] = "complete"
    elif event.stage == "helpdesk":
        state["helpdesk"] = event.status
    elif event.stage in {"tool_response", "response_restore", "agent_response"}:
        state["restore"] = "complete" if event.status == "complete" else event.status


def _render_timeline(events: list[dict[str, str]], target: Any | None = None) -> None:
    statuses = {key: "queued" for key, _ in STAGE_DEFINITIONS}
    for event in events:
        _event_state(
            WorkflowEvent(
                run_id=event["run_id"],
                stage=event["stage"],
                status=event["status"],  # type: ignore[arg-type]
                message=event["message"],
            ),
            statuses,
        )

    container = target.container() if target is not None else st.container()
    with container:
        cards = []
        for index, (key, title) in enumerate(STAGE_DEFINITIONS, start=1):
            status = statuses[key]
            icon = {
                "complete": "✓",
                "active": "↻",
                "blocked": "⛔",
                "failed": "!",
                "queued": "○",
            }[status]
            readable = {
                "complete": "Complete",
                "active": "In progress",
                "blocked": "Blocked",
                "failed": "Failed",
                "queued": "Not reached",
            }[status]
            display_title = (
                "3. Helpdesk not reached"
                if key == "helpdesk" and status == "queued"
                else title
            )
            cards.append(
                f"<div class='veil-stage veil-{status}' role='listitem' aria-live='polite'>"
                f"<span class='veil-stage-number'>Step {index} · {icon}</span>"
                f"<span class='veil-stage-title'>{display_title}</span>"
                f"<span class='veil-stage-status'>{readable}</span></div>"
            )
        st.markdown(
            STAGE_STYLE + "<div class='veil-flow' role='list'>" + "".join(cards) + "</div>",
            unsafe_allow_html=True,
        )


def _save_ticket_demo(*, show_blocked_path: bool, progress: Any) -> None:
    request = AgentRequest(
        message=st.session_state["veil_message"],
        requester=RequesterDetails(
            name=st.session_state["veil_name"],
            email=st.session_state["veil_email"],
            phone=st.session_state["veil_phone"],
        ),
    )
    safe_events: list[dict[str, str]] = []

    def on_event(event: WorkflowEvent) -> None:
        safe_events.append(
            {
                "run_id": event.run_id,
                "stage": event.stage,
                "status": event.status,
                "message": event.message,
            }
        )
        _render_timeline(safe_events, progress)

    try:
        additional_sensitive_values = tuple(
            value.strip()
            for value in st.session_state["veil_custom_sensitive_values"].splitlines()
            if value.strip()
        )
        run = run_ticket_demo(
            request=request,
            show_blocked_path=show_blocked_path,
            additional_sensitive_values=additional_sensitive_values,
            on_event=on_event,
        )
    except ValueError as error:
        _clear_trace()
        st.error(str(error))
        return

    st.session_state["veil_ticket_demo"] = {
        "run_id": run.run_id,
        "user_request": run.user_request,
        "agent_call": {
            "tool_name": run.agent_call.tool_name,
            "payload": run.agent_call.payload,
        },
        "events": safe_events,
        "result": run.result.to_dict(),
        "tool_payload": run.tool_payload,
        "agent_answer": run.agent_answer,
        "show_blocked_path": run.show_blocked_path,
    }


def _show_ticket_result(saved: dict[str, Any]) -> None:
    result = saved["result"]
    audit = result["audit"]
    st.subheader("What happened")
    _render_timeline(saved["events"])

    if audit["status"] == "allowed" and audit["leakage_count"] == 0:
        st.success(
            "The helpdesk received temporary labels instead of the original contact details. "
            "Veil restored them before the agent answered."
        )
        columns = st.columns(3)
        columns[0].metric("Details protected", audit["detection_count"])
        columns[1].metric("Original details sent to helpdesk", audit["leakage_count"])
        columns[2].metric("Veil processing time", f"{audit['added_latency_ms']:.3f} ms")
        st.markdown("**Answer the user sees**")
        st.info(saved["agent_answer"])
    elif audit["status"] == "blocked":
        st.error("Veil blocked the request. The helpdesk was not called.")
        st.metric("Helpdesk calls made", 0)
        if audit.get("blocked_reason"):
            st.caption("Veil could not confirm that the outgoing request was safe.")
    else:
        st.error("The workflow could not complete. No answer was created.")

    with st.expander("Show the proof from this workflow"):
        st.markdown("**What the local agent prepared**")
        st.code(json.dumps(saved["agent_call"], indent=2, ensure_ascii=False), language="json")
        st.markdown("**What the helpdesk actually received**")
        st.code(
            json.dumps(saved["tool_payload"], indent=2, ensure_ascii=False)
            if saved["tool_payload"] is not None
            else "The helpdesk was not reached, so it received no request.",
            language="json",
        )
        if result["tool_response"] is not None:
            st.markdown("**Helpdesk reply before restoration**")
            st.code(json.dumps(result["tool_response"], indent=2, ensure_ascii=False), language="json")
            st.markdown("**Reply returned to the trusted agent**")
            st.code(json.dumps(result["restored_response"], indent=2, ensure_ascii=False), language="json")
        if result["detections"]:
            st.markdown("**Details Veil detected**")
            st.dataframe(result["detections"], width="stretch", hide_index=True)
        st.caption(
            "This is a local synthetic-data simulation. Temporary labels are reversible "
            "tokens held in memory for this workflow; they are not encryption."
        )


def _show_helpdesk_workflow() -> None:
    st.header("Try the campus helpdesk workflow")
    st.write(
        "Enter a made-up message and contact details. The local agent will choose "
        "a ticket lookup when it finds a ticket ID, or submit a general support request. "
        "The screen shows exactly what the simulated helpdesk receives."
    )
    st.caption("Use synthetic data only. Nothing is sent to an external service.")

    st.text_area(
        "Your message (a ticket ID is optional)",
        key="veil_message",
        on_change=_clear_trace,
        height=100,
    )
    st.caption(
        "With a ticket ID, the agent looks up that ticket. Without one, the agent "
        "submits your message as a general support request."
    )
    st.text_area(
        "Other sensitive values to protect (optional, one exact value per line)",
        key="veil_custom_sensitive_values",
        on_change=_clear_trace,
        height=80,
        help="Use this for synthetic secrets outside the automatic email, phone, ID, and name checks. Include each value in your message too.",
    )
    details = st.columns(3)
    details[0].text_input("Synthetic name", key="veil_name", on_change=_clear_trace)
    details[1].text_input("Synthetic email", key="veil_email", on_change=_clear_trace)
    details[2].text_input("Synthetic phone", key="veil_phone", on_change=_clear_trace)

    buttons = st.columns(3)
    run_clicked = buttons[0].button("Run workflow", type="primary")
    blocked_clicked = buttons[1].button("Show blocked example")
    buttons[2].button("Reset demo", on_click=_reset_form)
    if run_clicked or blocked_clicked:
        _clear_trace()
        progress = st.empty()
        _save_ticket_demo(show_blocked_path=blocked_clicked, progress=progress)

    saved = st.session_state.get("veil_ticket_demo")
    if saved:
        _show_ticket_result(saved)


st.set_page_config(page_title="Veil | Privacy workflow", page_icon="🛡️", layout="wide")
st.title("Veil")
st.subheader("A privacy layer between an AI agent and its tools")
st.info(
    "Follow one local workflow: user → agent → Veil → simulated helpdesk → Veil → agent. "
    "All contact details are synthetic; no external AI or helpdesk is used."
)

for key, value in {
    "veil_message": DEMO_USER_REQUEST,
    "veil_custom_sensitive_values": "",
    "veil_name": DEMO_REQUESTER["name"],
    "veil_email": DEMO_REQUESTER["email"],
    "veil_phone": DEMO_REQUESTER["phone"],
}.items():
    st.session_state.setdefault(key, value)

_show_helpdesk_workflow()

with st.expander("What does Veil do?"):
    st.markdown(
        "The local agent prepares a request. Veil checks it, replaces selected personal "
        "details with temporary tokens, and verifies the outgoing payload. The simulated "
        "helpdesk sees that exact tokenized request. Veil restores known tokens only "
        "on the trusted path back to the agent. This small demo cannot guarantee detection "
        "of every kind of personal information."
    )
