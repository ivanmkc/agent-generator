"""Architecture Model module."""

from typing import List
from pydantic import BaseModel, Field


class ToolDetail(BaseModel):
    name: str = Field(..., description="Name of the tool.")
    purpose: str = Field(..., description="Description of what the tool does.")
    example: str = Field(..., description="Short example of when/how it is used.")


class ComponentDetail(BaseModel):
    name: str = Field(..., description="Name of the class or function.")
    responsibility: str = Field(
        ..., description="Description of its role in the system."
    )


class AgentArchitectureDocs(BaseModel):
    # Concise Summary
    core_philosophy: str = Field(
        ..., description="1-sentence summary of the design approach."
    )
    topology: str = Field(
        ...,
        description="The architectural topology (e.g., ReAct Loop, Sequential, Multi-Agent).",
    )
    key_tool_chain: List[str] = Field(
        ..., description="A concise list of the primary tools used."
    )

    # Extensive Breakdown
    architecture_overview: str = Field(
        ...,
        description="Detailed summary of the design pattern and component interaction philosophy.",
    )
    tool_chain_analysis: List[ToolDetail] = Field(
        ..., description="Detailed analysis of available tools."
    )
    call_hierarchy_ascii: str = Field(
        ..., description="Visual ASCII representation of the execution flow."
    )
    call_flow_example: str = Field(
        ...,
        description="Step-by-step walkthrough of a hypothetical execution scenario.",
    )
    key_components: List[ComponentDetail] = Field(
        ...,
        description="List of specific classes/functions and their responsibilities.",
    )

    def to_markdown(self) -> str:
        """Renders the model into the requested Markdown format."""

        # Format the concise tool list
        tools_list_str = ", ".join([f"`{t}`" for t in self.key_tool_chain])

        # Format tool chain table/list
        tools_analysis_md = ""
        for t in self.tool_chain_analysis:
            tools_analysis_md += (
                f"- **`{t.name}`**: {t.purpose} (e.g., *{t.example}*)\n"
            )

        # Format components list
        components_md = ""
        for c in self.key_components:
            components_md += f"- **`{c.name}`**: {c.responsibility}\n"

        md = f"""### Concise Summary
- **Core Philosophy:** {self.core_philosophy}
- **Topology:** {self.topology}
- **Key Tool Chain:** {tools_list_str}

---

### Extensive Architectural Breakdown

> **1. Architecture Overview**
> {self.architecture_overview.replace(chr(10), chr(10) + '> ')}
>
> **2. Tool Chain Analysis**
> {tools_analysis_md.replace(chr(10), chr(10) + '> ')}
>
> **3. Call Hierarchy & Flow**
> ```
> {self.call_hierarchy_ascii.replace(chr(10), chr(10) + '> ')}
> ```
>
> **4. Detailed Call Flow Example**
> {self.call_flow_example.replace(chr(10), chr(10) + '> ')}
>
> **5. Key Components**
> {components_md.replace(chr(10), chr(10) + '> ')}
"""
        return md
