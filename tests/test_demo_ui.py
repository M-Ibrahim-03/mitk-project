import tempfile
from pathlib import Path


def test_streamlit_demo_completes_a_protected_tool_call(monkeypatch) -> None:
    project_root = Path(__file__).resolve().parent.parent
    local_temp = project_root / "work" / "streamlit-temp"
    local_temp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TEMP", str(local_temp))
    monkeypatch.setenv("TMP", str(local_temp))
    monkeypatch.setattr(tempfile, "tempdir", str(local_temp))

    from streamlit.testing.v1 import AppTest

    app_test = AppTest.from_file(str(project_root / "veil" / "demo.py")).run(
        timeout=15
    )
    app_test.button[0].click().run(timeout=15)

    assert not app_test.exception
    demo_result = app_test.session_state["veil_demo_result"]
    result = demo_result["result"]
    assert result["audit"]["status"] == "allowed"
    assert result["audit"]["leakage_count"] == 0
    assert result["restored_response"]["echo"] == demo_result["original_payload"]
