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


def test_streamlit_demo_explains_the_result_in_plain_language(monkeypatch) -> None:
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
    protect_button = next(
        button
        for button in app_test.button
        if button.label == "2. Protect this sample"
    )
    protect_button.click().run(timeout=15)

    assert not app_test.exception
    assert app_test.success[0].value.startswith("Your sample is protected.")
    assert any("No detected originals reached the simulated tool" in item.value
               for item in app_test.caption)


def test_streamlit_demo_shows_benchmark_as_a_readable_scorecard(monkeypatch) -> None:
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
    benchmark_button = next(
        button for button in app_test.button if button.label == "Run sample tests"
    )
    benchmark_button.click().run(timeout=15)

    assert not app_test.exception
    metric_labels = {metric.label for metric in app_test.metric}
    assert {
        "Detection",
        "False alarms",
        "Originals sent to tool",
        "Correctly restored",
        "Median processing time",
        "Test examples",
    }.issubset(metric_labels)
    assert app_test.session_state["veil_benchmark"]["case_count"] == 7
    assert any("small synthetic test set" in item.value.lower()
               for item in app_test.caption)


def test_switching_sample_loads_its_own_example_data(monkeypatch) -> None:
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
    app_test.text_area[0].set_value('{"note": "my edited example"}').run(timeout=15)
    app_test.selectbox[0].select("The same detail appears more than once").run(
        timeout=15
    )

    assert not app_test.exception
    assert "riley@example.test" in app_test.text_area[0].value
    assert "my edited example" not in app_test.text_area[0].value
