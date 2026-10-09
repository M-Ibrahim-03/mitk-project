"""Streamlit entry point for the Veil interactive demo."""

from __future__ import annotations

import json

import streamlit as st

from veil.evaluation import BENCHMARK_PATH, evaluate_cases
from veil.gateway import VeilGateway
from veil.mock_tool import SimulatedTool


st.set_page_config(page_title="Veil | PII Tool Gateway", page_icon="🛡️", layout="wide")
st.title("Veil — Privacy Gateway for Agent Tools")
st.caption(
    "A local privacy layer that tokenizes synthetic PII before a simulated tool call."
)
st.info("Synthetic data only. This demo does not call an external tool or AI API.")

cases = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
case_by_name = {case["name"]: case for case in cases}
scenario_name = st.selectbox("Choose a synthetic scenario", list(case_by_name))
scenario = case_by_name[scenario_name]
payload_json = st.text_area(
    "Agent tool payload (JSON)",
    value=json.dumps(scenario["payload"], indent=2, ensure_ascii=False),
    height=250,
)

if st.button("Protect and call simulated tool", type="primary"):
    try:
        original_payload = json.loads(payload_json)
    except json.JSONDecodeError as error:
        st.error(f"Enter valid JSON: {error}")
    else:
        simulated_tool = SimulatedTool()
        gateway = VeilGateway(simulated_tool=simulated_tool)
        task = gateway.start_task()
        result = gateway.call_tool(task, "synthetic_demo_tool", original_payload)
        actual_tool_payload = (
            simulated_tool.received[-1].payload if simulated_tool.received else None
        )
        gateway.close_task(task)
        st.session_state["veil_demo_result"] = {
            "original_payload": original_payload,
            "actual_tool_payload": actual_tool_payload,
            "result": result.to_dict(),
        }

saved = st.session_state.get("veil_demo_result")
if saved:
    result = saved["result"]
    audit = result["audit"]
    st.subheader("Call audit")
    if audit["status"] == "allowed":
        st.success("Egress verified — the simulated tool received the sanitized payload.")
    else:
        st.error(f"Call blocked: {audit['blocked_reason']}")

    metric_columns = st.columns(5)
    metric_columns[0].metric("PII occurrences", audit["detection_count"])
    metric_columns[1].metric("Unique tokens", audit["unique_token_count"])
    metric_columns[2].metric("Leaked originals", audit["leakage_count"])
    metric_columns[3].metric("Restored occurrences", audit["restored_value_count"])
    metric_columns[4].metric("Added time", f"{audit['added_latency_ms']:.3f} ms")

    st.subheader("What happened")
    request_column, tool_column = st.columns(2)
    with request_column:
        st.markdown("**Original synthetic request**")
        st.code(json.dumps(saved["original_payload"], indent=2, ensure_ascii=False), language="json")
    with tool_column:
        st.markdown("**Exact payload captured by mock tool**")
        st.code(
            json.dumps(saved["actual_tool_payload"], indent=2, ensure_ascii=False)
            if saved["actual_tool_payload"] is not None
            else "No tool call was made.",
            language="json",
        )
    response_column, restored_column = st.columns(2)
    with response_column:
        st.markdown("**Mock tool response before restoration**")
        st.code(
            json.dumps(result["tool_response"], indent=2, ensure_ascii=False),
            language="json",
        )
    with restored_column:
        st.markdown("**Response after trusted-path restoration**")
        st.code(
            json.dumps(result["restored_response"], indent=2, ensure_ascii=False),
            language="json",
        )

    st.markdown("**Detections**")
    if result["detections"]:
        st.dataframe(result["detections"], width="stretch", hide_index=True)
    else:
        st.write("No selected PII types were detected in this payload.")

with st.expander("Synthetic benchmark"):
    if st.button("Run benchmark"):
        st.session_state["veil_benchmark"] = evaluate_cases()
    benchmark = st.session_state.get("veil_benchmark")
    if benchmark:
        st.json(benchmark)
        st.caption(benchmark["disclaimer"])

with st.expander("How to read the demo"):
    st.markdown(
        "- Tokens preserve repeated-value linkage within one task.\n"
        "- The token map stays in memory and is cleared when the task ends.\n"
        "- Only the trusted return path restores values.\n"
        "- Person-name detection uses local context patterns and a small fictional-name list; it is the least comprehensive recognizer."
    )

