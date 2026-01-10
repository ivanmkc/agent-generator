import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from vibeshare.models.litellm_model import LiteLLMModel

@pytest.mark.asyncio
async def test_litellm_model_predict():
    """Test that LiteLLMModel.predict calls litellm.acompletion correctly."""
    model_name = "test-model"
    prompt = "Hello, AI!"
    expected_response = "Hello, Human!"
    
    # Mock litellm.acompletion
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        # Setup mock response following OpenAI/LiteLLM structure
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = expected_response
        mock_acompletion.return_value = mock_response
        
        model = LiteLLMModel(model_name=model_name, temperature=0.5)
        result = await model.predict(prompt)
        
        # Assertions
        assert result == expected_response
        mock_acompletion.assert_called_once()
        
        # Verify arguments passed to acompletion
        args, kwargs = mock_acompletion.call_args
        assert kwargs["model"] == model_name
        assert kwargs["messages"] == [{"role": "user", "content": prompt}]
        assert kwargs["temperature"] == 0.5

@pytest.mark.asyncio
async def test_litellm_model_predict_empty_content():
    """Test handling of None content in response."""
    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_acompletion.return_value = mock_response
        
        model = LiteLLMModel(model_name="test-model")
        result = await model.predict("test")
        
        assert result == ""
