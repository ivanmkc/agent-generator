# Data Flow: From Raw Logs to Benchmark Viewer Sections

This graph illustrates how the raw benchmark results are processed, filtered, and transformed into the various sections visible in the Streamlit Benchmark Viewer.

```mermaid
graph TD
    %% --- Data Sources ---
    subgraph Storage [Disk Storage]
        ResultsJSON[("results.json<br/>(List of BenchmarkRunResult)")]
        TraceJSONL[("trace.jsonl<br/>(Detailed Event Logs)")]
    end

    %% --- Loading & Processing ---
    subgraph Processing [Data Loading & Processing]
        LoadFunc["load_results()"]
        RawDF[("Raw DataFrame")]
        FilterLogic["Sidebar Filters<br/>(Suite, Status, Generator)"]
        FilteredDF[("Filtered DataFrame")]
        
        ResultsJSON --> LoadFunc --> RawDF
        RawDF --> FilterLogic --> FilteredDF
    end

    %% --- Overview Section ---
    subgraph Overview [📊 Overview Mode]
        direction TB
        
        subgraph GlobalMetrics [Global Run Metrics]
            CalcGlobal["Aggregation:<br/>Count(Total), Count(Passed), Count(Crashes)"]
            MetricDisplay["Display Metrics:<br/>- Total Cases<br/>- Accuracy (Crashes=Fail)<br/>- Crashes"]
        end
        
        subgraph Breakdown [Detailed Breakdown Table]
            GroupLogic["GroupBy(Generator, Suite)<br/>+<br/>GroupBy(Generator) [Aggregate]"]
            CalcRates["Calculate:<br/>- Accuracy (System)<br/>- Accuracy (Valid)"]
            TableDisplay["Unified Table Display"]
        end

        FilteredDF --> CalcGlobal --> MetricDisplay
        FilteredDF --> GroupLogic --> CalcRates --> TableDisplay
    end

    %% --- Case Details Section ---
    subgraph Details [📝 Case Details Mode]
        CaseSelect["Select Case (Sidebar)"]
        SelectedRow["Selected Row (Single BenchmarkRunResult)"]
        
        subgraph HeaderInfo [Header]
            ExtractMeta["Extract: Latency, Status"]
            ParseRetries["Parse Trace Logs:<br/>Count 'write_file' attempts"]
            HeaderDisplay["Display: Name, Latency, Retries, Error"]
        end

        subgraph TabDiff [Tab: Diff & Code]
            GetFinal["Get Final Answer & Ground Truth"]
            GetAttempts["Extract Intermediate Code<br/>(from 'write_file' logs)"]
            DiffRender["Render: Side-by-Side or Unified Diff"]
        end

        subgraph TabLogs [Tab: Trace Logs]
            GetLogs["Get trace_logs"]
            GroupTools["Logic: Pair 'tool_use' with 'tool_result'"]
            FilterEvents["Filter: Event Types (Model, Tool, CLI)"]
            LogRender["Render: Expandable Log Entries"]
        end

        subgraph TabMeta [Tab: Metadata]
            RawJson["Display: usage_metadata & Raw Row JSON"]
        end

        FilteredDF --> CaseSelect --> SelectedRow
        
        SelectedRow --> ExtractMeta --> HeaderDisplay
        SelectedRow -->|trace_logs| ParseRetries --> HeaderDisplay
        
        SelectedRow --> GetFinal --> DiffRender
        SelectedRow -->|trace_logs| GetAttempts --> DiffRender
        
        SelectedRow -->|trace_logs| GetLogs --> GroupTools --> FilterEvents --> LogRender
        
        SelectedRow --> RawJson
    end

    %% --- Trace Data Injection ---
    TraceJSONL -.->|Enriched via load_traces()| RawDF
```
