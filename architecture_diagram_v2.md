# ADK Agent Architecture Diagram (State-Based)

This diagram illustrates the current "State-Centric" architecture where agents communicate primarily through the shared `session.state` using specific tools, rather than passing complex JSON objects in their output text.

```mermaid
graph TD
    UserRequest[User Request] --> SetupAgent(SetupAgent)
    SetupAgent --> PromptSanitizer(PromptSanitizerAgent)
    PromptSanitizer --> Decision{Use Index?}

    subgraph "Retrieval Phase"
        direction TB
        Decision -- Yes (Structured) --> IndexRetrieval[KnowledgeRetrievalAgent (Index)]
        IndexRetrieval -- "Tool: save_relevant_modules" --> StateModules[State: relevant_modules_json]
        StateModules --> ContextFetcher[KnowledgeContextFetcher]
        ContextFetcher -- "Fetches Docstrings" --> KnowledgeContext1[State: knowledge_context (Detailed)]

        Decision -- No (Baseline) --> ToolRetrieval[KnowledgeRetrievalAgent (Tools)]
        ToolRetrieval -- "Search & Summarize" --> KnowledgeContext2[State: knowledge_context (Summarized)]
    end

    KnowledgeContext1 --> Planner(Planner)
    KnowledgeContext2 --> Planner

    Planner -- "Tool: save_verification_plan" --> StateTestPrompt[State: test_prompt]
    Planner -- "Text Plan" --> CandidateCreator(CandidateCreator)

    subgraph "Implementation Loop"
        direction TB
        CandidateCreator -- "Tool: save_agent_code" --> StateCode[State: agent_code]
        StateCode --> Verifier(CodeBasedVerifier)
        StateTestPrompt --> Verifier
        Verifier -- "Run Agent & Analyze" --> StateResult[State: verification_result]
        StateResult --> CandidateCreator
    end

    Verifier -- "Success" --> FinalVerifier(CodeBasedFinalVerifier)
    FinalVerifier --> TeardownAgent(TeardownAgent)
    TeardownAgent --> FinalOutput[Final Response]

    classDef agent fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef tool fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef state fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;

    class SetupAgent,PromptSanitizer,IndexRetrieval,ToolRetrieval,ContextFetcher,Planner,CandidateCreator,Verifier,FinalVerifier,TeardownAgent agent;
    class StateModules,KnowledgeContext1,KnowledgeContext2,StateTestPrompt,StateCode,StateResult state;
```
