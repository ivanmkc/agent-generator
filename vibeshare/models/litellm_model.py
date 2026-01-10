from typing import Any
import litellm
from .model import Model

class LiteLLMModel(Model):
    """
    Model implementation using LiteLLM to support various LLM providers.
    """

    def __init__(self, model_name: str, **kwargs: Any):
        """
        Initialize the LiteLLMModel.

        Args:
            model_name (str): The name of the model to use (e.g., 'gpt-3.5-turbo', 'gemini-pro').
            **kwargs: Additional arguments to pass to litellm.completion (e.g., temperature, api_key).
        """
        self.model_name = model_name
        self.kwargs = kwargs

    async def predict(self, prompt: str, **kwargs) -> str:
        """
        Make a prediction based on the input prompt.

        Args:
            prompt (str): The input prompt.
            **kwargs: Overrides or additions to the arguments passed to litellm.acompletion.

        Returns:
            str: The generated response.
        """
        messages = [{"role": "user", "content": prompt}]
        
        # Merge self.kwargs with passed kwargs, letting passed kwargs take precedence
        merged_kwargs = {**self.kwargs, **kwargs}
        
        response = await litellm.acompletion(
            model=self.model_name,
            messages=messages,
            **merged_kwargs
        )
        
        # Extract content from the response
        # litellm follows OpenAI format. Content can be None if the finish reason is length or content filter etc,
        # but usually it's a string.
        content = response.choices[0].message.content
        if content is None:
            return ""
        return content