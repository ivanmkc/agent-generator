# Benchmark Tracking Architecture: API Keys & Failures

This document illustrates the end-to-end flow of how API keys and execution attempts (including failures) are tracked within the benchmark framework. This ensures that every attempt, whether successful or failed due to quota/errors, is attributed to the specific API key used.

## 1. Execution Context (`adk_context.py`)

We use `contextvars` to store execution metadata (like the API key) in a thread-safe way that propagates through async tasks without polluting function signatures.

```python
# benchmarks/answer_generators/adk_context.py
from contextvars import ContextVar
from typing import Dict, Any

# Stores: {"api_key": str, "key_id": str}
adk_execution_context: ContextVar[Dict[str, Any]] = ContextVar("adk_execution_context", default={})
```

## 2. Generator Execution (`AdkAnswerGenerator`)

The generator selects a key, sets the context, runs the agent, and crucially, wraps any failures in a custom exception that carries the `api_key_id`.

```python
# benchmarks/answer_generators/adk_answer_generator.py

    async def generate_answer(self, benchmark_case: BaseBenchmarkCase) -> GeneratedAnswer:
        # ... (setup schema) ...

        # 1. Select Key & Set Context
        if self.api_key_manager:
            current_key, api_key_id = self.api_key_manager.get_next_key_with_id(KeyType.GEMINI_API)
            if current_key:
                token = adk_execution_context.set({"api_key": current_key, "key_id": api_key_id})
        
        try:
            # 2. Run Agent (uses key from context via RotatingKeyGemini)
            response_text, trace_logs, usage_metadata = await self._run_agent_async(prompt)
            
            # 3. Report Success
            if api_key_id:
                self.api_key_manager.report_result(..., success=True)
                
        except Exception as e:
            # 4. Report Failure & RAISE WITH METADATA
            if api_key_id:
                self.api_key_manager.report_result(..., success=False, error_message=str(e))
            
            # Wrap original exception to bubble up the api_key_id
            raise BenchmarkGenerationError(
                f"ADK Generation failed: {e}", 
                original_exception=e, 
                api_key_id=api_key_id  # <--- Key ID attached here
            ) from e
            
        finally:
            if token:
                adk_execution_context.reset(token)

        # ... (process output) ...
        
        return GeneratedAnswer(..., api_key_id=api_key_id)
```

## 3. Custom Exception (`data_models.py`)

This exception bridges the gap between the low-level execution failure and the high-level orchestrator.

```python
# benchmarks/data_models.py

class BenchmarkGenerationError(Exception):
    """
    Raised when benchmark generation fails.
    Carries metadata about the failure context (e.g., used API key).
    """
    def __init__(self, message: str, original_exception: Exception, api_key_id: Optional[str] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.api_key_id = api_key_id
```

## 4. Orchestrator (`benchmark_orchestrator.py`)

The orchestrator manages the retry loop. It catches the `BenchmarkGenerationError` to record exactly which key failed before retrying.

```python
# benchmarks/benchmark_orchestrator.py

async def _run_single_benchmark(...):
    attempts_history: List[GenerationAttempt] = []

    # Manual Retry Loop
    for attempt_idx in range(max_retries + 1):
        try:
            generated_answer = await generator.generate_answer(case)

            # Record Success (get key from result)
            attempts_history.append(
                GenerationAttempt(
                    attempt_number=attempt_idx + 1,
                    status="success",
                    api_key_id=generated_answer.api_key_id,
                    # ...
                )
            )
            break

        except Exception as e:
            # Record Failure (EXTRACT key from exception)
            failed_key_id = None
            if isinstance(e, BenchmarkGenerationError):
                failed_key_id = e.api_key_id  # <--- Retrieving the key ID from the failed run
            
            attempts_history.append(
                GenerationAttempt(
                    attempt_number=attempt_idx + 1,
                    status="failure",
                    error_message=str(e),
                    api_key_id=failed_key_id, # <--- Storing it in history
                    # ...
                )
            )
            # ... (wait and retry) ...

    return BenchmarkRunResult(
        ...,
        generation_attempts=attempts_history  # <--- Full history of keys used
    )
```

## 5. Result Data Structure (`data_models.py`)

Finally, the `BenchmarkRunResult` contains a list of attempts, each with its own `api_key_id`, allowing the Viewer to visualize exactly which keys were rotated through during failures.

```python
# benchmarks/data_models.py

class GenerationAttempt(pydantic.BaseModel):
    attempt_number: int
    status: str       # "success" or "failure"
    error_message: Optional[str]
    api_key_id: Optional[str]  # <--- The key used for THIS specific attempt

class BenchmarkRunResult(pydantic.BaseModel):
    # ...
    generation_attempts: Optional[list[GenerationAttempt]]
    # (No top-level api_key_id, forcing analysis of attempts)
```
