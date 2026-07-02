from pathlib import Path

from traceshield_method.method.schemas import ToolEvent
from traceshield_method.method.adapters import ToolSemanticMapper


REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "python"
    / "traceshield_method"
    / "method"
    / "configs"
    / "tool_registry.yaml"
)


def mapper() -> ToolSemanticMapper:
    return ToolSemanticMapper(str(REGISTRY))


def test_read_file_mapping() -> None:
    event = mapper().map_event(ToolEvent(step_id=1, tool_name="read_file", args={"path": ".env"}))

    assert event.semantic_action == "read_file"
    assert event.target_resource == ".env"
    assert event.risk_level == "medium"


def test_network_post_mapping() -> None:
    event = mapper().map_event(ToolEvent(step_id=1, tool_name="network_post", args={"url": "https://example.com"}))

    assert event.tool_type == "network"
    assert event.semantic_action == "network_post"
    assert event.risk_level == "high"
    assert event.target_resource == "https://example.com"


def test_unknown_tool_mapping() -> None:
    event = mapper().map_event(ToolEvent(step_id=1, tool_name="evil_tool", args={}))

    assert event.tool_type == "unknown"
    assert event.semantic_action == "unknown_tool_call"
    assert event.risk_level == "high"


def test_get_value_extracts_first_argument() -> None:
    event = mapper().map_event(ToolEvent(step_id=1, tool_name="GetValue", args={"ARGUMENT": "diagnosisname, list"}))

    assert event.semantic_action == "read_database_field"
    assert event.target_resource == "diagnosisname"


def test_filter_db_includes_condition_columns() -> None:
    event = mapper().map_event(
        ToolEvent(
            step_id=1,
            tool_name="FilterDB",
            args={"DATABASE": "lab", "COLUMNS": ["labname", "labresulttime"]},
        )
    )

    assert event.semantic_action == "filter_database"
    assert event.target_resource == "lab;lab.labname;lab.labresulttime"


    event = mapper().map_event(ToolEvent(step_id=1, tool_name="read_file", args={}))

    assert event.target_resource is None
