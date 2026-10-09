"""Streamlit entry point for the beginner-friendly Veil demo."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from veil.evaluation import BENCHMARK_PATH, evaluate_cases
from veil.gateway import VeilGateway
from veil.mock_tool import SimulatedTool


SCENARIO_LABELS = {
    "nested_contact_request": "A contact request with several details",
    "duplicate_email_and_context_name": "The same detail appears more than once",
    "natural_language_with_non_lexicon_name": "A message with a name and account ID",
    "plain_safe_payload": "A request with no personal details",
    "unformatted_phone_and_labelled_name": "A name and phone number in a message",
    "punctuation_and_case_variants": "Details beside punctuation",
    "array_text_and_formatted_phone": "A list of messages with personal details",
}


def _clear_demo_result() -> None:
    """Avoid showing results for a sample that the user has since changed."""
    st.session_state.pop("veil_demo_result", None)


def _display_percent(value: object) -> str:
    return "Not available" if value is None else f"{value}%"


def _run_protected_sample(payload_json: str) -> None:
    st.session_state.pop("veil_demo_result", None)
    try:
        original_payload = json.loads(payload_json)
    except json.JSONDecodeError:
        st.error("This sample is not valid JSON. Check the optional data editor and try again.")
        return

    simulated_tool = SimulatedTool()
    gateway = VeilGateway(simulated_tool=simulated_tool)
    task = gateway.start_task()
    try:
        result = gateway.call_tool(task, "synthetic_demo_tool", original_payload)
    except Exception:
        st.error("Veil could not safely check this sample, so it did not continue.")
        return
    finally:
        gateway.close_task(task)

    actual_tool_payload = (
        simulated_tool.received[-1].payload if simulated_tool.received else None
    )
    st.session_state["veil_demo_result"] = {
        "original_payload": original_payload,
        "actual_tool_payload": actual_tool_payload,
        "result": result.to_dict(),
    }


def _show_demo_result(saved: dict[str, Any]) -> None:
    result = saved["result"]
    audit = result["audit"]
    st.header("3. Your result")

    protected = audit["status"] == "allowed" and audit["leakage_count"] == 0
    if protected:
        st.success("Your sample is protected.")
        if audit["detection_count"]:
            st.caption(
                "No detected originals reached the simulated tool. Veil replaced "
                "them with temporary labels and restored them in the reply."
            )
        else:
            st.caption(
                "Veil did not find any of the personal detail types this demo checks for."
            )
    elif audit["status"] == "blocked":
        st.error("Veil stopped this request because it could not confirm it was safe.")
        st.caption("The simulated tool was not called.")
    else:
        st.error("Veil found an issue while checking what would be sent to the tool.")

    metric_columns = st.columns(4)
    metric_columns[0].metric("Details detected", audit["detection_count"])
    metric_columns[1].metric("Detected originals sent", audit["leakage_count"])
    metric_columns[2].metric("Details restored", audit["restored_value_count"])
    metric_columns[3].metric("Time added", f"{audit['added_latency_ms']:.3f} ms")

    with st.expander("See the request and reply details"):
        st.write(
            "The first box is the sample you gave Veil. The second is exactly what "
            "the simulated tool received."
        )
        request_column, tool_column = st.columns(2)
        with request_column:
            st.markdown("**Your sample**")
            st.code(
                json.dumps(saved["original_payload"], indent=2, ensure_ascii=False),
                language="json",
            )
        with tool_column:
            st.markdown("**What the simulated tool received**")
            st.code(
                json.dumps(saved["actual_tool_payload"], indent=2, ensure_ascii=False)
                if saved["actual_tool_payload"] is not None
                else "No request was sent.",
                language="json",
            )

        response_column, restored_column = st.columns(2)
        with response_column:
            st.markdown("**The tool's reply before Veil restored details**")
            st.code(
                json.dumps(result["tool_response"], indent=2, ensure_ascii=False),
                language="json",
            )
        with restored_column:
            st.markdown("**The reply returned to the agent**")
            st.code(
                json.dumps(result["restored_response"], indent=2, ensure_ascii=False),
                language="json",
            )

        st.markdown("**What Veil noticed**")
        if result["detections"]:
            st.dataframe(result["detections"], width="stretch", hide_index=True)
        else:
            st.write("No selected personal detail types were found in this sample.")


def _show_benchmark() -> None:
    st.header("How Veil did on sample tests")
    st.write(
        "These checks use made-up examples to measure what Veil spots, blocks, "
        "and restores."
    )
    if st.button("Run sample tests"):
        st.session_state["veil_benchmark"] = evaluate_cases()

    benchmark = st.session_state.get("veil_benchmark")
    if not benchmark:
        st.caption("Run the checks to see the results.")
        return

    first_row = st.columns(4)
    first_row[0].metric(
        "Detection",
        _display_percent(benchmark["detection_recall_percent"]),
        help="How many planted personal details Veil found in these examples.",
    )
    first_row[1].metric("False alarms", benchmark["false_positive_count"])
    first_row[2].metric(
        "Originals sent to tool",
        benchmark["leakage_count"],
        help="How many planted original values appeared in the simulated tool's request.",
    )
    first_row[3].metric(
        "Correctly restored",
        _display_percent(benchmark["restoration_accuracy_percent"]),
    )

    second_row = st.columns(3)
    second_row[0].metric(
        "Median processing time", f"{benchmark['added_latency_p50_ms']} ms"
    )
    second_row[1].metric(
        "95th percentile time", f"{benchmark['added_latency_p95_ms']} ms"
    )
    second_row[2].metric("Test examples", benchmark["case_count"])
    st.caption(
        "Small synthetic test set only. These results do not prove that Veil can "
        "find every kind of personal information."
    )


st.set_page_config(page_title="Veil | Privacy demo", page_icon="🛡️", layout="wide")
st.title("Veil")
st.subheader("Keep personal details out of agent tool requests")
st.info(
    "This demo uses made-up examples and a simulated tool. It runs on this computer "
    "and does not call an external AI service."
)

st.header("Try Veil in 3 simple steps")
step_columns = st.columns(3)
step_columns[0].markdown("**1. Choose a sample**\n\nPick one of the made-up examples.")
step_columns[1].markdown("**2. Protect it**\n\nVeil checks it before the tool sees it.")
step_columns[2].markdown("**3. Read the result**\n\nSee whether anything was protected or blocked.")

cases = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
case_by_label = {
    SCENARIO_LABELS.get(case["name"], case["name"].replace("_", " ")): case
    for case in cases
}
scenario_label = st.selectbox(
    "1. Choose a made-up example",
    list(case_by_label),
    on_change=_clear_demo_result,
)
scenario = case_by_label[scenario_label]
default_payload = json.dumps(scenario["payload"], indent=2, ensure_ascii=False)
payload_key = f"veil_payload_json_{scenario['name']}"
with st.expander("Optional: inspect or edit the sample data"):
    st.caption("Only use made-up information in this local demo.")
    payload_json = st.text_area(
        "Sample data in JSON format",
        value=default_payload,
        height=200,
        key=payload_key,
        on_change=_clear_demo_result,
    )

if st.button("2. Protect this sample", type="primary"):
    _run_protected_sample(st.session_state.get(payload_key, default_payload))

saved_result = st.session_state.get("veil_demo_result")
if saved_result:
    _show_demo_result(saved_result)

st.divider()
_show_benchmark()

with st.expander("What do the words on this page mean?"):
    st.markdown(
        "- **Temporary labels:** short names that stand in for detected details while "
        "the request is with the simulated tool. Repeated details reuse the same label.\n"
        "- **Restored reply:** Veil puts the original made-up details back only when "
        "the reply returns to the trusted agent.\n"
        "- **Detection limit:** this demo checks selected emails, phone numbers, "
        "fictional names, and demo student IDs. Name detection is the least complete."
    )
