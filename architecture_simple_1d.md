# Simplified Linear Architecture (1D Flow)

This diagram highlights the linear progression of the agent workflow and the key state artifacts produced at each stage.

```text
[ USER REQUEST ]
      |
      v
1. SETUP & RETRIEVAL
   (Agents: Setup, Sanitizer, Retrieval)
   -> Updates State: [knowledge_context]
      |
      v
2. PLANNING
   (Agent: Planner)
   -> Updates State: [test_prompt]
      |
      v
3. IMPLEMENTATION LOOP <----------------------+
   (Agent: Candidate Creator)                 |
   -> Updates State: [agent_code]             |
      |                                       |
      v                                       |
   (Agent: Verifier)                          |
   -> Reads State: [agent_code] + [test_prompt]
   -> Updates State: [verification_result]    |
      |                                       |
      +---(If Failed)-------------------------+
      |
      v
4. FINALIZE
   (Agent: Final Verifier)
   -> Writes to Disk
      |
      v
[ FINAL RESPONSE ]
```
