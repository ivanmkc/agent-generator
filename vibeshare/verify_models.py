import asyncio
from vibeshare.config import MODELS
from vibeshare.core import get_key_type_for_model
from benchmarks.api_key_manager import API_KEY_MANAGER

async def verify_model(model):
    """
    Verifies if a model is working by sending a simple 'Hello' prompt.
    Returns (is_working, error_message).
    """
    print(f"Verifying {model.model_name}...")
    
    # Ensure API key logic is triggered just like in the main analysis
    key_type = get_key_type_for_model(model.model_name)
    key = None
    if key_type:
        key, _ = API_KEY_MANAGER.get_next_key_with_id(key_type)
        if not key:
            return False, f"No API key found for type {key_type}"

    predict_kwargs = {}
    if key:
        predict_kwargs["api_key"] = key

    try:
        # Short timeout for verification to fail fast
        # Note: LiteLLMModel.predict might not support timeout directly in all versions, 
        # but asyncio.wait_for handles the task level.
        response = await asyncio.wait_for(model.predict("Hello", **predict_kwargs), timeout=15.0)
        if response:
            return True, None
        else:
            return False, "Empty response"
    except Exception as e:
        return False, str(e)

async def run_verification():
    working_models = []
    broken_models = []

    print(f"Starting verification for {len(MODELS)} models...\n")
    
    # Run sequentially to avoid rate limits during verification and clear output
    for model in MODELS:
        is_working, error = await verify_model(model)
        if is_working:
            print(f"✅ {model.model_name}: Working")
            working_models.append(model)
        else:
            print(f"❌ {model.model_name}: Failed - {error}")
            broken_models.append((model.model_name, error))

    print("\n" + "="*30)
    print("VERIFICATION SUMMARY")
    print("="*30)
    print(f"Total Models: {len(MODELS)}")
    print(f"Working:      {len(working_models)}")
    print(f"Broken:       {len(broken_models)}")
    
    if broken_models:
        print("\nBroken Models Details:")
        for name, err in broken_models:
            print(f"- {name}: {err}")

    return working_models

if __name__ == "__main__":
    asyncio.run(run_verification())
