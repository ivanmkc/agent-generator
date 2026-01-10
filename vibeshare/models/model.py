import abc

class Model(abc.ABC):
    """Abstract base class for models in VibeShare."""

    @abc.abstractmethod
    async def predict(self, prompt: str, **kwargs) -> str:
        """Make a prediction based on the input data."""
        pass
