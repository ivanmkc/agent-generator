import pytest
from core.models import TraceLogEvent, TraceEventType

def test_trace_log_event_details_field():
    """
    Test that TraceLogEvent accepts and correctly stores the 'details' field.
    This prevents regression where the field was missing from the schema.
    """
    event = TraceLogEvent(
        type=TraceEventType.TOOL_USE,
        source="test",
        content="some content",
        details={"key": "value", "nested": 123}
    )
    
    assert event.details is not None
    assert event.details["key"] == "value"
    assert event.details["nested"] == 123

def test_trace_log_event_optional_details():
    """Test that details is optional."""
    event = TraceLogEvent(
        type=TraceEventType.MESSAGE,
        source="test",
        content="message"
    )
    assert event.details is None
