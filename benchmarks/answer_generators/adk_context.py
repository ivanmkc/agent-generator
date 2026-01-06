from contextvars import ContextVar
from typing import Optional, Dict, Any

"""
This module defines `contextvars` for managing execution-specific metadata
across asynchronous tasks within the benchmark framework.

Context variables provide a way to store and access data that is local to the
current asynchronous task, making them ideal for managing state (like API keys)
without passing them explicitly through every function call or relying on
thread-local storage, which is not suitable for async/await concurrency.
"""

adk_execution_context: ContextVar[Dict[str, Any]] = ContextVar(
    "adk_execution_context", 
    default={}
)