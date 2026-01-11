# ADK Agent Architecture Diagram

## High-Level Overview

This diagram illustrates the two workflow variants (`StructuredWorkflowAdk` and `BaselineWorkflowAdk`) sharing a common implementation loop but differing in their Knowledge Retrieval strategy.

```mermaid
graph TD
    UserRequest[User Request] --> SetupAgent(SetupAgent)
    SetupAgent --> PromptSanitizer(PromptSanitizerAgent)
    PromptSanitizer --> Decision{Use Index?}

    subgraph "Retrieval Phase"
        direction TB
        Decision -- Yes (Structured) --> IndexRetrieval[KnowledgeRetrievalAgent (Index)]
        IndexRetrieval -- "Selects Modules (JSON)" --> ContextFetcher[KnowledgeContextFetcher]
        ContextFetcher -- "Fetches Docstrings" --> KnowledgeContext1[Knowledge Context (Detailed)]

        Decision -- No (Baseline) --> ToolRetrieval[KnowledgeRetrievalAgent (Tools)]
        ToolRetrieval -- "Search & Summarize" --> KnowledgeContext2[Knowledge Context (Summarized)]
    end

    KnowledgeContext1 --> Planner(Planner)
    KnowledgeContext2 --> Planner

    Planner -- "PlanningResult (Steps + Test)" --> CandidateCreator(CandidateCreator)

    subgraph "Implementation Loop"
        direction TB
        CandidateCreator -- "CandidateSolution (Code)" --> SaveCode["Tool: save_agent_code"]
        SaveCode --> Verifier(CodeBasedVerifier)
        Verifier -- "Run Test Prompt" --> RunAgent["Tool: run_adk_agent"]
        RunAgent -- "VerificationResult" --> CandidateCreator
    end

    Verifier -- "Success" --> FinalVerifier(CodeBasedFinalVerifier)
    FinalVerifier --> TeardownAgent(TeardownAgent)
    TeardownAgent --> FinalOutput[Final Response]

    classDef agent fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef tool fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef data fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;

    class SetupAgent,PromptSanitizer,IndexRetrieval,ToolRetrieval,ContextFetcher,Planner,CandidateCreator,Verifier,FinalVerifier,TeardownAgent agent;
    class SaveCode,RunAgent tool;
    class UserRequest,KnowledgeContext1,KnowledgeContext2,FinalOutput data;
```

## Component Roles

1.  **SetupAgent:** Initializes the workspace directory.
2.  **PromptSanitizer:** Removes dangerous tool-calling instructions from the user prompt.
3.  **Knowledge Retrieval:**
    *   *Structured:* Uses a static YAML index to pinpoint modules, then programmatically fetches their full documentation. Fast but verbose.
    *   *Baseline:* Uses an LLM with search tools to explore and summarize. Slow but concise.
4.  **Planner:** Consumes the user request and knowledge context to produce a structured plan and a verification test case.
5.  **CandidateCreator:** Writes the code based on the plan.
6.  **CodeBasedVerifier:** deterministic execution of the generated agent using the Planner's test case.
7.  **FinalVerifier:** Persists the final solution to disk.
