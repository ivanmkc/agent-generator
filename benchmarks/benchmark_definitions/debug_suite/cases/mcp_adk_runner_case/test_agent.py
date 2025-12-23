import sys
import os
from google.adk.agents.base_agent import BaseAgent

# Add the current directory to sys.path to make fixed importable
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import fixed


def test_fixed_agent_returns_hello_world():
    agent = fixed.create_agent("dummy-model")
    assert agent.name == "hello_world_agent"
    assert isinstance(agent, BaseAgent)
    # The real BaseAgent might not have an 'invoke' method or it might behave differently.
    # But based on the 'fixed.py' implementation, HelloWorldAgent has an 'invoke' method.
    assert agent.invoke("Hi") == "Hello World"
    assert agent.invoke("Other") != "Hello World"
