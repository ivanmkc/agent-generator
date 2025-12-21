from google.adk.agents.base_agent import BaseAgent

class HelloWorldAgent(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name=name)

    def generate_response(self, user_input: str) -> str:
        if user_input == 'Hi':
            return 'Hello World'
        return 'I can only say Hello World for "Hi".'

    def invoke(self, user_input: str) -> str:
        return self.generate_response(user_input)

def create_agent(model_name: str) -> BaseAgent:
    return HelloWorldAgent(name="hello_world_agent")
