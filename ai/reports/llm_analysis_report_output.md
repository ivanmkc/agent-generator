# Forensic Root Cause Analysis Report

This report provides a hierarchical view of benchmark failures from the **last 10 runs**, analyzed by Gemini 2.0. The analysis is broken down by benchmark suite to highlight specific failure patterns.


```python
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import json
from IPython.display import display, HTML, Markdown

# Connect to Database
DB_PATH = "/Users/ivanmkc/Documents/code/agent-generator/benchmarks/analysis_cache.db"
conn = sqlite3.connect(DB_PATH)

# Load Data
query = """
SELECT 
    run_id, 
    generator, 
    suite, 
    benchmark_name, 
    attempt_number, 
    llm_root_cause,
    llm_analysis
FROM failures
WHERE llm_root_cause IS NOT NULL
ORDER BY run_id DESC, generator, suite, benchmark_name, attempt_number
"""
df = pd.read_sql_query(query, conn)

# Parse JSON forensics
def parse_forensics(row):
    try:
        data = json.loads(row['llm_analysis'])
        return pd.Series({
            'narrative': data.get('explanation', 'N/A'),
            'citations': " | ".join(data.get('evidence', data.get('citations', []))),
            'tool_audit': str(data.get('tool_audit', ''))
        })
    except:
        return pd.Series({'narrative': 'Parse Error', 'citations': 'N/A', 'tool_audit': 'N/A'})

forensics = df.apply(parse_forensics, axis=1)
df = pd.concat([df, forensics], axis=1)

print(f"Total failures analyzed: {len(df)}")
```

    Total failures analyzed: 726


## Global Failure Trends


```python
if not df.empty:
    plt.figure(figsize=(12, 6))
    df['llm_root_cause'].value_counts().plot(kind='bar', color='teal')
    plt.title('Global Root Cause Distribution')
    plt.ylabel('Count')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3)
    plt.show()
else:
    print("No analyzed failures found.")
```


    
![png](llm_analysis_report_output_files/llm_analysis_report_output_3_0.png)
    


## Analysis by Benchmark Suite
Breakdown of root causes for each test suite.


```python
if not df.empty:
    suites = df['suite'].unique()
    for suite in suites:
        display(Markdown(f"### Suite: `{suite}`"))
        suite_df = df[df['suite'] == suite]
        
        # Chart
        plt.figure(figsize=(10, 4))
        suite_df['llm_root_cause'].value_counts().plot(kind='barh', color='salmon')
        plt.title(f'Root Causes: {suite}')
        plt.xlabel('Count')
        plt.show()
        
        # Detailed Table (Top 5 Failures)
        display(Markdown(f"**Top Failure Examples ({suite}):**"))
        display(suite_df[['generator', 'benchmark_name', 'llm_root_cause', 'narrative']].head(5))
        display(Markdown("---"))
else:
    print("No data available.")
```


### Suite: `fix_errors`



    
![png](llm_analysis_report_output_files/llm_analysis_report_output_5_1.png)
    



**Top Failure Examples (fix_errors):**



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>generator</th>
      <th>benchmark_name</th>
      <th>llm_root_cause</th>
      <th>narrative</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>ADK_CODING_V38(Decoupled)</td>
      <td>01: A minimal LlmAgent.</td>
      <td>Hallucination</td>
      <td>The agent hallucinated the module `google.adk....</td>
    </tr>
    <tr>
      <th>1</th>
      <td>ADK_CODING_V38(Decoupled)</td>
      <td>02: An LlmAgent with a simple function tool.</td>
      <td>Schema Violation</td>
      <td>The agent failed because the LlmAgent construc...</td>
    </tr>
    <tr>
      <th>2</th>
      <td>ADK_CODING_V38(Decoupled)</td>
      <td>03: An LlmAgent that uses output_schema to enf...</td>
      <td>Hallucination</td>
      <td>The agent initially produced code that attempt...</td>
    </tr>
    <tr>
      <th>3</th>
      <td>ADK_CODING_V38(Decoupled)</td>
      <td>04: A SequentialAgent orchestrating two simple...</td>
      <td>Hallucination</td>
      <td>The agent hallucinated the arguments for the `...</td>
    </tr>
    <tr>
      <th>4</th>
      <td>ADK_CODING_V38(Decoupled)</td>
      <td>05: A ParallelAgent running two agents concurr...</td>
      <td>Schema Violation</td>
      <td>The coding expert provided a Linter class inst...</td>
    </tr>
  </tbody>
</table>
</div>



---



### Suite: `api_understanding`



    
![png](llm_analysis_report_output_files/llm_analysis_report_output_5_6.png)
    



**Top Failure Examples (api_understanding):**



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>generator</th>
      <th>benchmark_name</th>
      <th>llm_root_cause</th>
      <th>narrative</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>23</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What is the `CallbackContext` object?</td>
      <td>Logic Error</td>
      <td>The agent successfully identified the relevant...</td>
    </tr>
    <tr>
      <th>24</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What is the `InvocationContext` object?</td>
      <td>Logic Error</td>
      <td>The agent successfully identified the `Invocat...</td>
    </tr>
    <tr>
      <th>25</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What is the abstract base class for implementi...</td>
      <td>Hallucination (Ignored Context)</td>
      <td>The agent initially selected `BaseAgent` as th...</td>
    </tr>
    <tr>
      <th>26</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What is the base class for all tools?</td>
      <td>Logic Error</td>
      <td>The agent initially correctly identifies `goog...</td>
    </tr>
    <tr>
      <th>27</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What is the base class for managing and dynami...</td>
      <td>Context Starvation</td>
      <td>The agent attempted to find the base class for...</td>
    </tr>
  </tbody>
</table>
</div>



---



### Suite: `configure_adk_features_mc`



    
![png](llm_analysis_report_output_files/llm_analysis_report_output_5_11.png)
    



**Top Failure Examples (configure_adk_features_mc):**



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>generator</th>
      <th>benchmark_name</th>
      <th>llm_root_cause</th>
      <th>narrative</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>53</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>How do you configure an app to support pausing...</td>
      <td>Logic Error</td>
      <td>The agent successfully fetched documentation f...</td>
    </tr>
    <tr>
      <th>54</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>How do you correctly construct a user message ...</td>
      <td>Logic Error</td>
      <td>The agent correctly identified the relevant mo...</td>
    </tr>
    <tr>
      <th>55</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>How do you enable `CodeExecutionTool` via conf...</td>
      <td>Hallucination (Ignored Context)</td>
      <td>The `seed_selector_agent` correctly identified...</td>
    </tr>
    <tr>
      <th>56</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>How do you enable `GoogleSearchTool` via confi...</td>
      <td>Schema Violation</td>
      <td>The agent successfully fetched relevant module...</td>
    </tr>
    <tr>
      <th>57</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>How do you enable `VertexAISearchTool` via con...</td>
      <td>Schema Violation</td>
      <td>The agent successfully loaded the necessary in...</td>
    </tr>
  </tbody>
</table>
</div>



---



### Suite: `diagnose_setup_errors_mc`



    
![png](llm_analysis_report_output_files/llm_analysis_report_output_5_16.png)
    



**Top Failure Examples (diagnose_setup_errors_mc):**



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>generator</th>
      <th>benchmark_name</th>
      <th>llm_root_cause</th>
      <th>narrative</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>125</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>How should sub-agents be passed to `Sequential...</td>
      <td>Logic Error</td>
      <td>The agent correctly fetched the relevant modul...</td>
    </tr>
    <tr>
      <th>126</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What data type does the `input_schema` argumen...</td>
      <td>Logic Error</td>
      <td>The agent correctly identified that the `input...</td>
    </tr>
    <tr>
      <th>127</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What is the correct parameter name for enforci...</td>
      <td>Logic Error</td>
      <td>The agent correctly identified that the `forma...</td>
    </tr>
    <tr>
      <th>128</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What is the primary reason this `LlmAgent` ins...</td>
      <td>Schema Violation</td>
      <td>The `knowledge_expert` agent, after receiving ...</td>
    </tr>
    <tr>
      <th>129</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>Which argument is missing in this `Runner` ini...</td>
      <td>Schema Violation</td>
      <td>The agent failed to produce a valid JSON outpu...</td>
    </tr>
  </tbody>
</table>
</div>



---



### Suite: `predict_runtime_behavior_mc`



    
![png](llm_analysis_report_output_files/llm_analysis_report_output_5_21.png)
    



**Top Failure Examples (predict_runtime_behavior_mc):**



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>generator</th>
      <th>benchmark_name</th>
      <th>llm_root_cause</th>
      <th>narrative</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>151</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>In what order will the callbacks and agent out...</td>
      <td>Logic Error</td>
      <td>The agent correctly identified the relevant mo...</td>
    </tr>
    <tr>
      <th>152</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>Is the `name` attribute mutable?...</td>
      <td>Schema Violation</td>
      <td>The agent failed to provide an answer in the f...</td>
    </tr>
    <tr>
      <th>153</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>Predict the error (if any) when running the fo...</td>
      <td>Logic Error</td>
      <td>The agent correctly identified that duplicate ...</td>
    </tr>
    <tr>
      <th>154</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>Predict the error:...</td>
      <td>Hallucination (Ignored Context)</td>
      <td>The agent correctly identified that the `Gener...</td>
    </tr>
    <tr>
      <th>155</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>Predict the error:...</td>
      <td>Hallucination (Ignored Context)</td>
      <td>The agent correctly identified that the `Gener...</td>
    </tr>
  </tbody>
</table>
</div>



---



### Suite: `debug_single`



    
![png](llm_analysis_report_output_files/llm_analysis_report_output_5_26.png)
    



**Top Failure Examples (debug_single):**



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>generator</th>
      <th>benchmark_name</th>
      <th>llm_root_cause</th>
      <th>narrative</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>164</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What does `RunConfig.proactivity` control?...</td>
      <td>Infrastructure</td>
      <td>The agent failed due to a RESOURCE_EXHAUSTED e...</td>
    </tr>
    <tr>
      <th>165</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What does `RunConfig.proactivity` control?...</td>
      <td>Schema Violation</td>
      <td>The agent correctly identified the answer and ...</td>
    </tr>
    <tr>
      <th>166</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What does `RunConfig.proactivity` control?...</td>
      <td>Schema Violation</td>
      <td>The agent correctly identified the answer and ...</td>
    </tr>
    <tr>
      <th>167</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What does `RunConfig.proactivity` control?...</td>
      <td>Schema Violation</td>
      <td>The agent successfully identified the correct ...</td>
    </tr>
    <tr>
      <th>168</th>
      <td>ADK_KNOWLEDGE_V37(Decoupled)</td>
      <td>What does `RunConfig.proactivity` control?...</td>
      <td>Schema Violation</td>
      <td>The agent failed to return a valid JSON object...</td>
    </tr>
  </tbody>
</table>
</div>



---



### Suite: `debug_suite`



    
![png](llm_analysis_report_output_files/llm_analysis_report_output_5_31.png)
    



**Top Failure Examples (debug_suite):**



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>generator</th>
      <th>benchmark_name</th>
      <th>llm_root_cause</th>
      <th>narrative</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>690</th>
      <td>ADK_STATISTICAL_V36(Mixed)</td>
      <td>22: Implement a custom LogicAgent from scratch.</td>
      <td>Logic Error</td>
      <td>The agent initially failed because the `create...</td>
    </tr>
    <tr>
      <th>691</th>
      <td>ADK_STATISTICAL_V35(Mixed)</td>
      <td>22: Implement a custom LogicAgent from scratch.</td>
      <td>Logic Error</td>
      <td>The agent initially failed because it did not ...</td>
    </tr>
    <tr>
      <th>692</th>
      <td>ADK_STATISTICAL_V35(Mixed)</td>
      <td>What is the foundational class for all agents ...</td>
      <td>Schema Violation</td>
      <td>The finalizer agent produced a JSON object tha...</td>
    </tr>
    <tr>
      <th>693</th>
      <td>ADK_STATISTICAL_V35(Mixed)</td>
      <td>22: Implement a custom LogicAgent from scratch.</td>
      <td>Logic Error</td>
      <td>The agent initially failed because it did not ...</td>
    </tr>
    <tr>
      <th>694</th>
      <td>ADK_STATISTICAL_V35(Mixed)</td>
      <td>What is the foundational class for all agents ...</td>
      <td>Infrastructure</td>
      <td>The agent failed due to a 429 RESOURCE_EXHAUST...</td>
    </tr>
  </tbody>
</table>
</div>



---

