import asyncio
from pathlib import Path
from benchmarks.answer_generators.adk_tools import AdkTools

async def main():
    # Use current directory as workspace for this test
    workspace = Path(".").resolve()
    tools = AdkTools(workspace)
    
    modules = [
        "google.adk.agents.llm_agent",
        "google.adk.agents.base_agent",
        "google.adk.events"
    ]
    
    for mod in modules:
        print(f"\n{'='*20} Help for {mod} {'='*20}")
        help_text = await tools.get_module_help(mod)
        print(help_text)

if __name__ == "__main__":
    asyncio.run(main())

