from typing import Dict, Optional
from asyncio import Semaphore
from tenacity import retry, stop_after_attempt, wait_exponential

from models.model import Model
from data_models import VibeshareResult
from benchmarks.api_key_manager import API_KEY_MANAGER, KeyType
from cache import CACHE_MANAGER

def get_key_type_for_model(model_name: str) -> Optional[KeyType]:
    """
    Determines the appropriate API KeyType based on the model name substring.
    
    Args:
        model_name (str): The full model name (e.g., 'gemini/gemini-2.5-flash').

    Returns:
        Optional[KeyType]: The matching KeyType enum or None if not found.
    """
    model_lower = model_name.lower()
    if "gemini" in model_lower:
        return KeyType.GEMINI_API
    if "gpt" in model_lower or "o3" in model_lower:
        return KeyType.OPENAI_API
    if "claude" in model_lower:
        return KeyType.ANTHROPIC_API
    if "grok" in model_lower or "xai/" in model_lower:
        return KeyType.XAI_API
    if "llama" in model_lower or "groq/" in model_lower:
        return KeyType.GROQ_API
    return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def run_inference_task(model: Model, prompt_data: Dict[str, str], semaphore: Semaphore):
    """
    Runs prediction if not cached.
    Saves raw result to cache.
    """
    prompt = prompt_data.get("prompt", "")
    
    # 1. Check Cache
    cached_data = CACHE_MANAGER.get(model.model_name, prompt)
    if cached_data:
        print(f"Cache Hit: {model.model_name} | {prompt[:20]}...")
        return

    # 2. Run Inference
    response = None
    error_msg = None
    success = False
    key: Optional[str] = None
    key_id: Optional[str] = None
    
    # Determine which key type is needed for this model
    key_type = get_key_type_for_model(model.model_name)
    
    if key_type:
        key, key_id = API_KEY_MANAGER.get_next_key_with_id(key_type)
        if not key:
             error_msg = f"No active API keys available for {key_type.value}."
    
    predict_kwargs = {}
    if key:
        predict_kwargs["api_key"] = key

    if not error_msg:
        try:
            async with semaphore:
                response = await model.predict(prompt, **predict_kwargs)
            success = True
        except Exception as e:
            error_msg = str(e)
            success = False
            if key_type and key_id:
                API_KEY_MANAGER.report_result(key_type, key_id, False, error_message=error_msg)
        else:
             if key_type and key_id:
                API_KEY_MANAGER.report_result(key_type, key_id, True)

    # 3. Save to Cache
    raw_result = {
        "response": response,
        "success": success,
        "error_message": error_msg
    }
    CACHE_MANAGER.set(model.model_name, prompt, raw_result)
    
    status = "SUCCESS" if success else "ERROR"
    print(f"Inference: {model.model_name} | Status: {status}")

def create_vibeshare_result(model_name: str, prompt_data: Dict[str, str]) -> VibeshareResult:
    """
    Constructs a VibeshareResult object by retrieving the raw response from the cache.

    Args:
        model_name (str): The name of the model.
        prompt_data (Dict[str, str]): The prompt dictionary containing 'prompt' and 'category'.

    Returns:
        VibeshareResult: The structured result object.
    """
    prompt = prompt_data.get("prompt", "")
    category = prompt_data.get("category", "unknown")
    
    cached_data = CACHE_MANAGER.get(model_name, prompt)
    
    if not cached_data:
        return VibeshareResult(
            category=category,
            prompt=prompt,
            model_name=model_name,
            success=False,
            error_message="Not found in cache"
        )
        
    return VibeshareResult(
        category=category,
        prompt=prompt,
        model_name=model_name,
        response=cached_data.get("response"),
        success=cached_data.get("success", False),
        error_message=cached_data.get("error_message")
    )
