"""Test Benchmark Definitions Reality module."""

import pytest
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps.app import EventsCompactionConfig, App
from google.adk.agents.sequential_agent import SequentialAgent
from pydantic import ValidationError


def test_reality_cache_ttl_seconds_validation():
    """
    Verifies that ContextCacheConfig uses 'ttl_seconds' and raises
    ValidationError when passed a string.
    Matches benchmark: diagnose_setup_errors_mc:cache_ttl_string
    """
    with pytest.raises(ValidationError) as excinfo:
        # We use experimental decorator so might trigger warning, but we care about exception
        ContextCacheConfig(ttl_seconds="not-an-int")

    assert "Input should be a valid integer" in str(excinfo.value)

    # Verify 'ttl' is NOT a field (raises Extra inputs not permitted)
    with pytest.raises(ValidationError) as excinfo:
        ContextCacheConfig(ttl=1800)
    assert "Extra inputs are not permitted" in str(excinfo.value)


def test_reality_compaction_interval_zero_allowed():
    """
    Verifies that EventsCompactionConfig ALLOWS 0 for compaction_interval.
    Matches benchmark: diagnose_setup_errors_mc:compaction_interval_zero
    """
    # Should NOT raise ValidationError
    config = EventsCompactionConfig(compaction_interval=0, overlap_size=1)
    assert config.compaction_interval == 0


def test_reality_sequential_empty_subagents():
    """
    Verifies that SequentialAgent allows empty sub_agents.
    Matches benchmark: diagnose_setup_errors_mc:sequential_empty_subagents
    """
    # Should NOT raise error
    agent = SequentialAgent(name="empty_seq")
    assert agent.sub_agents == []
