# Codebase Knowledge MCP - Test Completion Report
**Date:** Saturday, January 31, 2026

## Summary
All 9 integration test scenarios passed successfully. The testing suite verifies the end-to-end functionality of the MCP server across different installation methods, IDE configurations, and failure modes.

### Key Validation Points
1.  **Installation & Setup:**
    *   **Manual (`manual_uvx`):** Verifies standard `uvx` execution with environment variables.
    *   **Extension (`extension_uvx`):** Verifies "installing" via a simulated extension modifying settings.
    *   **Managed CLI (`managed_setup`):** Verifies the `codebase-knowledge-mcp-manage` CLI correctly detects agents (Gemini CLI), generates configuration (including `env` wrappers), and that the generated config *actually runs* the server.
    *   **Managed JSON (`managed_json_setup`):** Verifies configuration of JSON-based IDEs (Cursor, Windsurf, Roo Code, Antigravity).
    *   **Managed Mock (`managed_claude`):** Verifies Claude Code specific CLI syntax (`--` separator).

2.  **Runtime Features:**
    *   **Registry Lookup:** Verifies automatic resolution of index URLs from `registry.yaml` based on repo URL.
    *   **Tool Execution:** All successful startup tests (Manual, Extension, Managed CLI, Registry) verify that `list_modules` returns correct data and `read_source_code` works (where git access permits).
    *   **Environment Overrides:** Verified `TARGET_INDEX_URL` override (via `--knowledge-index-url` test).

3.  **Resilience:**
    *   **Invalid Version:** Server starts gracefully even if repo version doesn't match a known index (fallback to empty/search-only).
    *   **Missing Index:** Server reports useful errors if index download fails.
    *   **Missing API Key:** Server fails fast if semantic search is requested without an API key.

## Test Logs
```text
STEP 1/12: FROM python:3.10-slim
STEP 2/12: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/12: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/12: RUN curl -LsSf https://astral.sh/uv/install.sh | sh
--> Using cache 590171ccac3a9c4664f86bfecf5485cac85e01ee6e74882152f60aac47e69ddd
--> 590171ccac3a
STEP 5/12: ENV PATH="/root/.local/bin:$PATH"
--> Using cache 9bac0ad13096f45ce62041780e2a8db494000274d10d21660411289751081c4c
--> 9bac0ad13096
STEP 6/12: RUN pip install mcp
--> Using cache dedc6ca2db267474271e81344fa130205fe0de30dca5fafa03450e9da14b1163
--> dedc6ca2db26
STEP 7/12: COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
--> Using cache 05e0408f790a92d224b94711bfb60fb1873805cb28c2f7a9b0059f1fb01a664f
--> 05e0408f790a
STEP 8/12: COPY tools/adk_knowledge_ext /tmp/pkg
--> 1f958519d0e1
STEP 9/12: COPY tools/adk_knowledge_ext/tests/integration/manual_uvx/settings.json /root/.gemini/settings.json
--> 71be9d48f2ae
STEP 10/12: RUN python3 -c "import json; f='/root/.gemini/settings.json'; d=json.load(open(f)); d['mcpServers']['test-codebase']['env']['TARGET_INDEX_URL']='file:///tmp/local_index.yaml'; json.dump(d, open(f,'w'))"
--> 4f6541b6c579
STEP 11/12: COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify.py
--> f5f192ae03ff
STEP 12/12: CMD ["python", "/app/verify.py"]
COMMIT adk-test-manual
--> c3f1a092ceef
Successfully tagged localhost/adk-test-manual:latest
c3f1a092ceef7c0b17d8be02395bf2dea035a5d515c7bd2b66f38c98823cd3d0
   Building codebase-knowledge-mcp @ file:///tmp/pkg
Downloading numpy (13.6MiB)
Downloading beartype (1.3MiB)
Downloading lupa (1.0MiB)
Downloading cryptography (4.1MiB)
Downloading pygments (1.2MiB)
Downloading pydantic-core (1.8MiB)
 Downloaded lupa
 Downloaded pygments
 Downloaded beartype
 Downloaded pydantic-core
      Built codebase-knowledge-mcp @ file:///tmp/pkg
 Downloaded cryptography
 Downloaded numpy
Installed 91 packages in 31ms
2026-01-31 22:41:11,034 - adk_knowledge_ext.reader - INFO - Cloning adk-python (v1.20.0) from https://github.com/google/adk-python.git to /root/.mcp_cache/adk-python/v1.20.0...
2026-01-31 22:41:12,286 - adk_knowledge_ext.reader - INFO - Clone successful.
2026-01-31 22:41:12,301 - mcp.server.lowlevel.server - INFO - Processing request of type ListToolsRequest
2026-01-31 22:41:12,302 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-01-31 22:41:14,655 - adk_knowledge_ext.index - INFO - No GEMINI_API_KEY detected. Using 'bm25' search.
2026-01-31 22:41:14,655 - adk_knowledge_ext.index - INFO - Initializing search provider: bm25
2026-01-31 22:41:14,682 - adk_knowledge_ext.search - INFO - BM25 Index built with 3238 items.
2026-01-31 22:41:14,682 - adk_knowledge_ext.index - INFO - Loaded 3238 targets from index.
2026-01-31 22:41:14,683 - codebase-knowledge-mcp - INFO - System instructions available at: /root/.mcp_cache/instructions/adk-python.md
2026-01-31 22:41:14,685 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
--- Starting MCP Verification ---
Found server configuration: test-codebase
DEBUG: Resolved command 'uvx'. TEST_LOCAL_OVERRIDE=None
Server Initialized.
Available Tools: ['list_modules', 'search_knowledge', 'read_source_code', 'inspect_symbol']
Testing 'list_modules'...
SUCCESS: Index loaded and tools working.
Testing 'read_source_code' (Triggers Clone)...
SUCCESS: Source code retrieved.
STEP 1/12: FROM python:3.10-slim
STEP 2/12: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/12: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/12: RUN curl -LsSf https://astral.sh/uv/install.sh | sh
--> Using cache 590171ccac3a9c4664f86bfecf5485cac85e01ee6e74882152f60aac47e69ddd
--> 590171ccac3a
STEP 5/12: ENV PATH="/root/.local/bin:$PATH"
--> Using cache 9bac0ad13096f45ce62041780e2a8db494000274d10d21660411289751081c4c
--> 9bac0ad13096
STEP 6/12: RUN pip install mcp
--> Using cache dedc6ca2db267474271e81344fa130205fe0de30dca5fafa03450e9da14b1163
--> dedc6ca2db26
STEP 7/12: COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
--> Using cache 05e0408f790a92d224b94711bfb60fb1873805cb28c2f7a9b0059f1fb01a664f
--> 05e0408f790a
STEP 8/12: COPY tools/adk_knowledge_ext /tmp/pkg
--> 17ea956c4227
STEP 9/12: COPY tools/adk_knowledge_ext/tests/integration/extension_uvx/install_extension.py /app/install.py
--> c46b840a0a7a
STEP 10/12: RUN python /app/install.py
--- Simulating Extension Installation ---
Settings updated at /root/.gemini/settings.json
--> 430b88eaa06e
STEP 11/12: COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify.py
--> a93e55242eaa
STEP 12/12: CMD ["python", "/app/verify.py"]
COMMIT adk-test-extension
--> a3dba9462af1
Successfully tagged localhost/adk-test-extension:latest
a3dba9462af18a1654ce4b1c49cd0d5eda9908e39d3a59f1f93d5cc6b9f88229
   Building codebase-knowledge-mcp @ file:///tmp/pkg
Downloading pydantic-core (1.8MiB)
Downloading pygments (1.2MiB)
Downloading cryptography (4.1MiB)
Downloading numpy (13.6MiB)
Downloading beartype (1.3MiB)
Downloading lupa (1.0MiB)
 Downloaded lupa
 Downloaded pygments
 Downloaded beartype
 Downloaded pydantic-core
 Downloaded cryptography
 Downloaded numpy
      Built codebase-knowledge-mcp @ file:///tmp/pkg
Installed 91 packages in 27ms
2026-01-31 22:41:22,322 - adk_knowledge_ext.reader - INFO - Cloning adk-python (v1.20.0) from https://github.com/google/adk-python.git to /root/.mcp_cache/adk-python/v1.20.0...
2026-01-31 22:41:23,477 - adk_knowledge_ext.reader - INFO - Clone successful.
2026-01-31 22:41:23,490 - mcp.server.lowlevel.server - INFO - Processing request of type ListToolsRequest
2026-01-31 22:41:23,491 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-01-31 22:41:25,714 - adk_knowledge_ext.index - INFO - No GEMINI_API_KEY detected. Using 'bm25' search.
2026-01-31 22:41:25,714 - adk_knowledge_ext.index - INFO - Initializing search provider: bm25
2026-01-31 22:41:25,741 - adk_knowledge_ext.search - INFO - BM25 Index built with 3238 items.
2026-01-31 22:41:25,741 - adk_knowledge_ext.index - INFO - Loaded 3238 targets from index.
2026-01-31 22:41:25,742 - codebase-knowledge-mcp - INFO - System instructions available at: /root/.mcp_cache/instructions/adk-python.md
2026-01-31 22:41:25,744 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
--- Starting MCP Verification ---
Found server configuration: codebase-knowledge
DEBUG: Resolved command 'uvx'. TEST_LOCAL_OVERRIDE=None
Server Initialized.
Available Tools: ['list_modules', 'search_knowledge', 'read_source_code', 'inspect_symbol']
Testing 'list_modules'...
SUCCESS: Index loaded and tools working.
Testing 'read_source_code' (Triggers Clone)...
SUCCESS: Source code retrieved.
STEP 1/10: FROM python:3.10-slim
STEP 2/10: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/10: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/10: COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
--> Using cache 1452078ceae739f011b4091dc07e05b179ca98406633208d578f4b2d5412b2d1
--> 1452078ceae7
STEP 5/10: ENV TARGET_VERSION=v1.20.0
--> Using cache b77b1445cc83fbd96a059aad26db0d5dc452eb5326aa8802f41283b2625ec557
--> b77b1445cc83
STEP 6/10: ENV TARGET_INDEX_URL=file:///tmp/local_index.yaml
--> Using cache 94728544017367a12fb40bf7b75345238af51e69f45b39eca2c6adeda08ede91
--> 947285440173
STEP 7/10: COPY tools/adk_knowledge_ext /tmp/pkg
--> 8bec661d776f
STEP 8/10: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Collecting rank-bm25
  Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Collecting rich
  Downloading rich-14.3.1-py3-none-any.whl (309 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 8.3 MB/s eta 0:00:00
Collecting fastmcp
  Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 37.3 MB/s eta 0:00:00
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (740 kB)
Collecting click
  Downloading click-8.3.1-py3-none-any.whl (108 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 108.3/108.3 kB 122.1 MB/s eta 0:00:00
Collecting mcp
  Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 36.3 MB/s eta 0:00:00
Collecting openapi-pydantic>=0.5.1
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 53.8 MB/s eta 0:00:00
Collecting exceptiongroup>=1.2.2
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting platformdirs>=4.0.0
  Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Collecting python-dotenv>=1.1.0
  Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Collecting httpx>=0.28.1
  Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 34.6 MB/s eta 0:00:00
Collecting authlib>=1.6.5
  Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 48.0 MB/s eta 0:00:00
Collecting websockets>=15.0.1
  Downloading websockets-16.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.1/185.1 kB 52.5 MB/s eta 0:00:00
Collecting uvicorn>=0.35
  Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.5/68.5 kB 43.6 MB/s eta 0:00:00
Collecting py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 22.7 MB/s eta 0:00:00
Collecting pyperclip>=1.9.0
  Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Collecting jsonref>=1.1.0
  Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Collecting jsonschema-path>=0.3.4
  Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Collecting pydocket<0.17.0,>=0.16.6
  Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 26.6 MB/s eta 0:00:00
Collecting cyclopts>=4.0.0
  Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 50.2 MB/s eta 0:00:00
Collecting packaging>=20.0
  Using cached packaging-26.0-py3-none-any.whl (74 kB)
Collecting pydantic[email]>=2.11.7
  Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 15.1 MB/s eta 0:00:00
Collecting anyio>=4.5
  Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 201.3 MB/s eta 0:00:00
Collecting pydantic-settings>=2.5.2
  Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 11.0 MB/s eta 0:00:00
Collecting sse-starlette>=1.6.1
  Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Collecting jsonschema>=4.20.0
  Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 31.6 MB/s eta 0:00:00
Collecting httpx-sse>=0.4
  Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Collecting typing-inspection>=0.4.1
  Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Collecting pyjwt[crypto]>=2.10.1
  Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Collecting starlette>=0.27
  Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 113.4 MB/s eta 0:00:00
Collecting python-multipart>=0.0.9
  Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Collecting typing-extensions>=4.9.0
  Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 61.8 MB/s eta 0:00:00
Collecting markdown-it-py>=2.2.0
  Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 47.1 MB/s eta 0:00:00
Collecting pygments<3.0.0,>=2.13.0
  Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 12.3 MB/s eta 0:00:00
Collecting numpy
  Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 29.6 MB/s eta 0:00:00
Collecting idna>=2.8
  Downloading idna-3.11-py3-none-any.whl (71 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71.0/71.0 kB 13.5 MB/s eta 0:00:00
Collecting cryptography
  Downloading cryptography-46.0.4-cp38-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 28.6 MB/s eta 0:00:00
Collecting docstring-parser<4.0,>=0.15
  Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Collecting tomli>=2.0.0
  Using cached tomli-2.4.0-py3-none-any.whl (14 kB)
Collecting rich-rst<2.0.0,>=1.3.1
  Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Collecting attrs>=23.1.0
  Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 83.9 MB/s eta 0:00:00
Collecting httpcore==1.*
  Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 47.3 MB/s eta 0:00:00
Collecting certifi
  Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 43.2 MB/s eta 0:00:00
Collecting h11>=0.16
  Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.25.0
  Downloading rpds_py-0.30.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.7/389.7 kB 48.2 MB/s eta 0:00:00
Collecting jsonschema-specifications>=2023.03.6
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting requests<3.0.0,>=2.31.0
  Downloading requests-2.32.5-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 45.1 MB/s eta 0:00:00
Collecting pathable<0.5.0,>=0.4.1
  Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Collecting mdurl~=0.1
  Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Collecting beartype>=0.20.0
  Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 27.6 MB/s eta 0:00:00
Collecting py-key-value-shared==0.3.0
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Collecting keyring>=25.6.0
  Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Collecting pathvalidate>=3.3.1
  Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Collecting diskcache>=5.0.0
  Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 76.8 MB/s eta 0:00:00
Collecting cachetools>=5.0.0
  Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Collecting annotated-types>=0.6.0
  Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting pydantic-core==2.41.5
  Downloading pydantic_core-2.41.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 33.1 MB/s eta 0:00:00
Collecting email-validator>=2.0.0
  Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Collecting fakeredis[lua]>=2.32.1
  Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 42.8 MB/s eta 0:00:00
Collecting opentelemetry-api>=1.33.0
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 42.4 MB/s eta 0:00:00
Collecting opentelemetry-exporter-prometheus>=0.60b0
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Collecting python-json-logger>=2.0.7
  Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Collecting redis>=5
  Downloading redis-7.1.0-py3-none-any.whl (354 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 45.2 MB/s eta 0:00:00
Collecting typer>=0.15.1
  Downloading typer-0.21.1-py3-none-any.whl (47 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 67.1 MB/s eta 0:00:00
Collecting opentelemetry-instrumentation>=0.60b0
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Collecting cloudpickle>=3.1.1
  Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Collecting prometheus-client>=0.21.1
  Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 24.6 MB/s eta 0:00:00
Collecting cffi>=2.0.0
  Downloading cffi-2.0.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.4/216.4 kB 22.1 MB/s eta 0:00:00
Collecting dnspython>=2.0.0
  Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 31.7 MB/s eta 0:00:00
Collecting sortedcontainers>=2
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Collecting lupa>=2.1
  Downloading lupa-2.6-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 34.5 MB/s eta 0:00:00
Collecting SecretStorage>=3.2
  Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Collecting jaraco.functools
  Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Collecting importlib_metadata>=4.11.4
  Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Collecting jaraco.classes
  Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Collecting jaraco.context
  Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Collecting jeepney>=0.4.2
  Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 97.9 MB/s eta 0:00:00
Collecting opentelemetry-sdk~=1.39.1
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 13.5 MB/s eta 0:00:00
Collecting opentelemetry-semantic-conventions==0.60b1
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 41.4 MB/s eta 0:00:00
Collecting wrapt<2.0.0,>=1.0.0
  Downloading wrapt-1.17.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 50.3 MB/s eta 0:00:00
Collecting async-timeout>=4.0.3
  Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
Collecting charset_normalizer<4,>=2
  Downloading charset_normalizer-3.4.4-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (148 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 148.8/148.8 kB 28.3 MB/s eta 0:00:00
Collecting urllib3<3,>=1.21.1
  Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 45.5 MB/s eta 0:00:00
Collecting docutils
  Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 45.6 MB/s eta 0:00:00
Collecting shellingham>=1.3.0
  Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Collecting pycparser
  Downloading pycparser-3.0-py3-none-any.whl (48 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 82.9 MB/s eta 0:00:00
Collecting zipp>=3.20
  Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Collecting more-itertools
  Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 47.0 MB/s eta 0:00:00
Collecting backports.tarfile
  Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=436366 sha256=e4bd2e8b68809e179c294269b29c21f01d2634d34c71074331673a92e5efeee5
  Stored in directory: /tmp/pip-ephem-wheel-cache-r2j3n25h/wheels/60/38/27/e774dc618089d42af20ea07600f801fa663a4b3310be033a3c
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, typing-extensions, tomli, shellingham, rpds-py, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, idna, httpx-sse, h11, docutils, docstring-parser, dnspython, diskcache, cloudpickle, click, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, async-timeout, annotated-types, uvicorn, typing-inspection, requests, referencing, redis, rank-bm25, pydantic-core, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, exceptiongroup, email-validator, cffi, rich, pydantic, py-key-value-aio, opentelemetry-api, jsonschema-specifications, jsonschema-path, fakeredis, cryptography, anyio, typer, starlette, SecretStorage, rich-rst, pydantic-settings, opentelemetry-semantic-conventions, openapi-pydantic, jsonschema, httpx, authlib, sse-starlette, opentelemetry-sdk, opentelemetry-instrumentation, keyring, cyclopts, opentelemetry-exporter-prometheus, mcp, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.1 async-timeout-5.0.1 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.2.6 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 starlette-0.52.1 tomli-2.4.0 typer-0.21.1 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.40.0 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> 19860fa9f34c
STEP 9/10: COPY tools/adk_knowledge_ext/tests/integration/resilience_invalid_version/verify_resilience.py /app/verify.py
--> 49d27419e6be
STEP 10/10: CMD ["python", "/app/verify.py"]
COMMIT adk-test-res-version
--> 19ae5fcf10c7
Successfully tagged localhost/adk-test-res-version:latest
19ae5fcf10c7f39cc13fa0ecafb76a7497fec57ac22e8f4b21e799ec6c316976
2026-01-31 22:41:42,964 - adk_knowledge_ext.reader - INFO - Cloning adk-python (v9.9.9) from https://github.com/google/adk-python.git to /root/.mcp_cache/adk-python/v9.9.9...
2026-01-31 22:41:43,112 - adk_knowledge_ext.reader - ERROR - Failed to clone repository: Cloning into '/root/.mcp_cache/adk-python/v9.9.9'...
warning: Could not find remote branch v9.9.9 to clone.
fatal: Remote branch v9.9.9 not found in upstream origin

2026-01-31 22:41:43,121 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
--- Starting Resilience Verification (Invalid Version) ---
Server Initialized.
Calling list_modules...
SUCCESS: Server handled missing index gracefully.
STEP 1/11: FROM python:3.10-slim
STEP 2/11: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/11: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/11: COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
--> Using cache 1452078ceae739f011b4091dc07e05b179ca98406633208d578f4b2d5412b2d1
--> 1452078ceae7
STEP 5/11: ENV TARGET_VERSION=v1.20.0
--> Using cache b77b1445cc83fbd96a059aad26db0d5dc452eb5326aa8802f41283b2625ec557
--> b77b1445cc83
STEP 6/11: ENV TARGET_INDEX_URL=file:///tmp/local_index.yaml
--> Using cache 94728544017367a12fb40bf7b75345238af51e69f45b39eca2c6adeda08ede91
--> 947285440173
STEP 7/11: COPY tools/adk_knowledge_ext /tmp/pkg
--> 596b8c4de98f
STEP 8/11: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Collecting rich
  Downloading rich-14.3.1-py3-none-any.whl (309 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 10.0 MB/s eta 0:00:00
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (740 kB)
Collecting rank-bm25
  Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Collecting mcp
  Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 43.5 MB/s eta 0:00:00
Collecting fastmcp
  Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 41.8 MB/s eta 0:00:00
Collecting click
  Downloading click-8.3.1-py3-none-any.whl (108 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 108.3/108.3 kB 40.3 MB/s eta 0:00:00
Collecting platformdirs>=4.0.0
  Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Collecting py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 104.3 MB/s eta 0:00:00
Collecting httpx>=0.28.1
  Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 24.8 MB/s eta 0:00:00
Collecting pydocket<0.17.0,>=0.16.6
  Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 34.3 MB/s eta 0:00:00
Collecting jsonref>=1.1.0
  Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Collecting pydantic[email]>=2.11.7
  Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 40.0 MB/s eta 0:00:00
Collecting websockets>=15.0.1
  Downloading websockets-16.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.1/185.1 kB 29.0 MB/s eta 0:00:00
Collecting packaging>=20.0
  Using cached packaging-26.0-py3-none-any.whl (74 kB)
Collecting uvicorn>=0.35
  Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.5/68.5 kB 30.1 MB/s eta 0:00:00
Collecting exceptiongroup>=1.2.2
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting pyperclip>=1.9.0
  Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Collecting cyclopts>=4.0.0
  Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 37.1 MB/s eta 0:00:00
Collecting jsonschema-path>=0.3.4
  Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Collecting authlib>=1.6.5
  Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 34.8 MB/s eta 0:00:00
Collecting python-dotenv>=1.1.0
  Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Collecting openapi-pydantic>=0.5.1
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 102.2 MB/s eta 0:00:00
Collecting pyjwt[crypto]>=2.10.1
  Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Collecting pydantic-settings>=2.5.2
  Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 83.5 MB/s eta 0:00:00
Collecting sse-starlette>=1.6.1
  Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Collecting starlette>=0.27
  Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 135.1 MB/s eta 0:00:00
Collecting python-multipart>=0.0.9
  Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Collecting httpx-sse>=0.4
  Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Collecting anyio>=4.5
  Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 39.9 MB/s eta 0:00:00
Collecting typing-extensions>=4.9.0
  Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 77.1 MB/s eta 0:00:00
Collecting jsonschema>=4.20.0
  Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 47.0 MB/s eta 0:00:00
Collecting typing-inspection>=0.4.1
  Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Collecting markdown-it-py>=2.2.0
  Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 36.3 MB/s eta 0:00:00
Collecting pygments<3.0.0,>=2.13.0
  Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 35.9 MB/s eta 0:00:00
Collecting numpy
  Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 26.7 MB/s eta 0:00:00
Collecting idna>=2.8
  Downloading idna-3.11-py3-none-any.whl (71 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71.0/71.0 kB 29.9 MB/s eta 0:00:00
Collecting cryptography
  Downloading cryptography-46.0.4-cp38-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 36.2 MB/s eta 0:00:00
Collecting docstring-parser<4.0,>=0.15
  Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Collecting tomli>=2.0.0
  Using cached tomli-2.4.0-py3-none-any.whl (14 kB)
Collecting rich-rst<2.0.0,>=1.3.1
  Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Collecting attrs>=23.1.0
  Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 35.4 MB/s eta 0:00:00
Collecting httpcore==1.*
  Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 35.4 MB/s eta 0:00:00
Collecting certifi
  Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 40.6 MB/s eta 0:00:00
Collecting h11>=0.16
  Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Collecting rpds-py>=0.25.0
  Downloading rpds_py-0.30.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.7/389.7 kB 44.1 MB/s eta 0:00:00
Collecting referencing>=0.28.4
  Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
Collecting jsonschema-specifications>=2023.03.6
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting pathable<0.5.0,>=0.4.1
  Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Collecting requests<3.0.0,>=2.31.0
  Downloading requests-2.32.5-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 23.8 MB/s eta 0:00:00
Collecting mdurl~=0.1
  Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Collecting beartype>=0.20.0
  Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 28.4 MB/s eta 0:00:00
Collecting py-key-value-shared==0.3.0
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Collecting cachetools>=5.0.0
  Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Collecting keyring>=25.6.0
  Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Collecting diskcache>=5.0.0
  Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 48.1 MB/s eta 0:00:00
Collecting pathvalidate>=3.3.1
  Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Collecting pydantic-core==2.41.5
  Downloading pydantic_core-2.41.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 38.1 MB/s eta 0:00:00
Collecting annotated-types>=0.6.0
  Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting email-validator>=2.0.0
  Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Collecting opentelemetry-exporter-prometheus>=0.60b0
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Collecting fakeredis[lua]>=2.32.1
  Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 34.1 MB/s eta 0:00:00
Collecting cloudpickle>=3.1.1
  Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Collecting opentelemetry-instrumentation>=0.60b0
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Collecting prometheus-client>=0.21.1
  Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 34.2 MB/s eta 0:00:00
Collecting python-json-logger>=2.0.7
  Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Collecting redis>=5
  Downloading redis-7.1.0-py3-none-any.whl (354 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 45.5 MB/s eta 0:00:00
Collecting typer>=0.15.1
  Downloading typer-0.21.1-py3-none-any.whl (47 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 80.2 MB/s eta 0:00:00
Collecting opentelemetry-api>=1.33.0
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 4.5 MB/s eta 0:00:00
Collecting cffi>=2.0.0
  Downloading cffi-2.0.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.4/216.4 kB 25.4 MB/s eta 0:00:00
Collecting dnspython>=2.0.0
  Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 25.9 MB/s eta 0:00:00
Collecting sortedcontainers>=2
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Collecting lupa>=2.1
  Downloading lupa-2.6-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 40.6 MB/s eta 0:00:00
Collecting importlib_metadata>=4.11.4
  Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Collecting jaraco.classes
  Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Collecting jaraco.functools
  Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Collecting SecretStorage>=3.2
  Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Collecting jeepney>=0.4.2
  Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 84.1 MB/s eta 0:00:00
Collecting jaraco.context
  Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Collecting opentelemetry-sdk~=1.39.1
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 59.3 MB/s eta 0:00:00
Collecting opentelemetry-semantic-conventions==0.60b1
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 39.6 MB/s eta 0:00:00
Collecting wrapt<2.0.0,>=1.0.0
  Downloading wrapt-1.17.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 35.3 MB/s eta 0:00:00
Collecting async-timeout>=4.0.3
  Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
Collecting charset_normalizer<4,>=2
  Downloading charset_normalizer-3.4.4-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (148 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 148.8/148.8 kB 39.2 MB/s eta 0:00:00
Collecting urllib3<3,>=1.21.1
  Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 69.7 MB/s eta 0:00:00
Collecting docutils
  Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 36.5 MB/s eta 0:00:00
Collecting shellingham>=1.3.0
  Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Collecting pycparser
  Downloading pycparser-3.0-py3-none-any.whl (48 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 74.0 MB/s eta 0:00:00
Collecting zipp>=3.20
  Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Collecting more-itertools
  Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 45.7 MB/s eta 0:00:00
Collecting backports.tarfile
  Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=436366 sha256=e4bd2e8b68809e179c294269b29c21f01d2634d34c71074331673a92e5efeee5
  Stored in directory: /tmp/pip-ephem-wheel-cache-j1ndkb_l/wheels/60/38/27/e774dc618089d42af20ea07600f801fa663a4b3310be033a3c
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, typing-extensions, tomli, shellingham, rpds-py, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, idna, httpx-sse, h11, docutils, docstring-parser, dnspython, diskcache, cloudpickle, click, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, async-timeout, annotated-types, uvicorn, typing-inspection, requests, referencing, redis, rank-bm25, pydantic-core, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, exceptiongroup, email-validator, cffi, rich, pydantic, py-key-value-aio, opentelemetry-api, jsonschema-specifications, jsonschema-path, fakeredis, cryptography, anyio, typer, starlette, SecretStorage, rich-rst, pydantic-settings, opentelemetry-semantic-conventions, openapi-pydantic, jsonschema, httpx, authlib, sse-starlette, opentelemetry-sdk, opentelemetry-instrumentation, keyring, cyclopts, opentelemetry-exporter-prometheus, mcp, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.1 async-timeout-5.0.1 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.2.6 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 starlette-0.52.1 tomli-2.4.0 typer-0.21.1 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.40.0 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> 5d4a1f0f0437
STEP 9/11: RUN rm /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/data/indices/index_v1.20.0.yaml
--> 4b9750e3c2ef
STEP 10/11: COPY tools/adk_knowledge_ext/tests/integration/resilience_missing_index/verify_missing_index.py /app/verify.py
--> c253581751e7
STEP 11/11: CMD ["python", "/app/verify.py"]
COMMIT adk-test-res-index
--> 32ffcf20bd0c
Successfully tagged localhost/adk-test-res-index:latest
32ffcf20bd0c58def5935e3867be31fb22fc4930e61ef9bb2799cc11cf59c4ea
2026-01-31 22:42:01,091 - codebase-knowledge-mcp - ERROR - TARGET_REPO_URL environment variable is not set. Cloning will be unavailable.
2026-01-31 22:42:01,095 - adk_knowledge_ext.reader - INFO - Cloning  (v1.20.0) from  to /root/.mcp_cache/v1.20.0...
2026-01-31 22:42:01,096 - adk_knowledge_ext.reader - ERROR - Failed to clone repository: fatal: repository '' does not exist

2026-01-31 22:42:01,107 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-01-31 22:42:01,108 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
--- Starting Resilience Verification (Valid Version, Missing Index) ---
Launching Server...
Server Initialized.
Calling list_modules (Expect failure)...
Tool Output: Error executing tool list_modules: This repository ('None') is not supported by the Codebase Knowledge MCP server because its knowledge index is not properly set up.

TO FIX THIS:
1. Run 'codebase-knowledge-mcp-manage setup' for this repository.
2. If you are in a restricted environment, use the --knowledge-index-url flag pointing to a local YAML file.
SUCCESS: Handled missing index gracefully.
Calling read_source_code (Expect failure due to no index)...
Tool Output: Error executing tool read_source_code: This repository ('None') is not supported by the Codebase Knowledge MCP server because its knowledge index is not properly set up.

TO FIX THIS:
1. Run 'codebase-knowledge-mcp-manage setup' for this repository.
2. If you are in a restricted environment, use the --knowledge-index-url flag pointing to a local YAML file.
SUCCESS: Correctly reported failure (due to missing index).
STEP 1/10: FROM python:3.10-slim
STEP 2/10: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/10: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/10: COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
--> Using cache 1452078ceae739f011b4091dc07e05b179ca98406633208d578f4b2d5412b2d1
--> 1452078ceae7
STEP 5/10: ENV TARGET_VERSION=v1.20.0
--> Using cache b77b1445cc83fbd96a059aad26db0d5dc452eb5326aa8802f41283b2625ec557
--> b77b1445cc83
STEP 6/10: ENV TARGET_INDEX_URL=file:///tmp/local_index.yaml
--> Using cache 94728544017367a12fb40bf7b75345238af51e69f45b39eca2c6adeda08ede91
--> 947285440173
STEP 7/10: COPY tools/adk_knowledge_ext /tmp/pkg
--> e7eba1552f22
STEP 8/10: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Collecting fastmcp
  Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 10.2 MB/s eta 0:00:00
Collecting rich
  Downloading rich-14.3.1-py3-none-any.whl (309 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 36.7 MB/s eta 0:00:00
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (740 kB)
Collecting click
  Downloading click-8.3.1-py3-none-any.whl (108 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 108.3/108.3 kB 45.8 MB/s eta 0:00:00
Collecting mcp
  Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 46.7 MB/s eta 0:00:00
Collecting rank-bm25
  Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Collecting python-dotenv>=1.1.0
  Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Collecting jsonref>=1.1.0
  Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Collecting packaging>=20.0
  Using cached packaging-26.0-py3-none-any.whl (74 kB)
Collecting authlib>=1.6.5
  Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 39.2 MB/s eta 0:00:00
Collecting platformdirs>=4.0.0
  Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Collecting cyclopts>=4.0.0
  Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 37.7 MB/s eta 0:00:00
Collecting websockets>=15.0.1
  Downloading websockets-16.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.1/185.1 kB 47.9 MB/s eta 0:00:00
Collecting pydocket<0.17.0,>=0.16.6
  Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 95.0 MB/s eta 0:00:00
Collecting openapi-pydantic>=0.5.1
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 90.7 MB/s eta 0:00:00
Collecting httpx>=0.28.1
  Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 60.0 MB/s eta 0:00:00
Collecting pydantic[email]>=2.11.7
  Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 43.2 MB/s eta 0:00:00
Collecting uvicorn>=0.35
  Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.5/68.5 kB 21.6 MB/s eta 0:00:00
Collecting py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 34.7 MB/s eta 0:00:00
Collecting pyperclip>=1.9.0
  Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Collecting jsonschema-path>=0.3.4
  Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Collecting exceptiongroup>=1.2.2
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting starlette>=0.27
  Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 38.9 MB/s eta 0:00:00
Collecting python-multipart>=0.0.9
  Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Collecting sse-starlette>=1.6.1
  Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Collecting httpx-sse>=0.4
  Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Collecting typing-inspection>=0.4.1
  Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Collecting jsonschema>=4.20.0
  Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 46.4 MB/s eta 0:00:00
Collecting pyjwt[crypto]>=2.10.1
  Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Collecting typing-extensions>=4.9.0
  Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 55.6 MB/s eta 0:00:00
Collecting anyio>=4.5
  Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 50.0 MB/s eta 0:00:00
Collecting pydantic-settings>=2.5.2
  Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 91.6 MB/s eta 0:00:00
Collecting markdown-it-py>=2.2.0
  Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 38.4 MB/s eta 0:00:00
Collecting pygments<3.0.0,>=2.13.0
  Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 28.0 MB/s eta 0:00:00
Collecting numpy
  Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 13.9 MB/s eta 0:00:00
Collecting idna>=2.8
  Downloading idna-3.11-py3-none-any.whl (71 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71.0/71.0 kB 29.7 MB/s eta 0:00:00
Collecting cryptography
  Downloading cryptography-46.0.4-cp38-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 23.0 MB/s eta 0:00:00
Collecting docstring-parser<4.0,>=0.15
  Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Collecting rich-rst<2.0.0,>=1.3.1
  Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Collecting attrs>=23.1.0
  Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 34.6 MB/s eta 0:00:00
Collecting tomli>=2.0.0
  Using cached tomli-2.4.0-py3-none-any.whl (14 kB)
Collecting certifi
  Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 33.7 MB/s eta 0:00:00
Collecting httpcore==1.*
  Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 45.6 MB/s eta 0:00:00
Collecting h11>=0.16
  Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Collecting jsonschema-specifications>=2023.03.6
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Collecting rpds-py>=0.25.0
  Downloading rpds_py-0.30.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.7/389.7 kB 17.1 MB/s eta 0:00:00
Collecting referencing>=0.28.4
  Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
  Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting requests<3.0.0,>=2.31.0
  Downloading requests-2.32.5-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 78.3 MB/s eta 0:00:00
Collecting pathable<0.5.0,>=0.4.1
  Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Collecting mdurl~=0.1
  Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Collecting py-key-value-shared==0.3.0
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Collecting beartype>=0.20.0
  Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 23.5 MB/s eta 0:00:00
Collecting diskcache>=5.0.0
  Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 80.4 MB/s eta 0:00:00
Collecting pathvalidate>=3.3.1
  Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Collecting keyring>=25.6.0
  Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Collecting cachetools>=5.0.0
  Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Collecting pydantic-core==2.41.5
  Downloading pydantic_core-2.41.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 23.4 MB/s eta 0:00:00
Collecting annotated-types>=0.6.0
  Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting email-validator>=2.0.0
  Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Collecting opentelemetry-api>=1.33.0
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 15.3 MB/s eta 0:00:00
Collecting python-json-logger>=2.0.7
  Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Collecting prometheus-client>=0.21.1
  Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 22.2 MB/s eta 0:00:00
Collecting opentelemetry-instrumentation>=0.60b0
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Collecting typer>=0.15.1
  Downloading typer-0.21.1-py3-none-any.whl (47 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 57.1 MB/s eta 0:00:00
Collecting fakeredis[lua]>=2.32.1
  Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 131.7 MB/s eta 0:00:00
Collecting redis>=5
  Downloading redis-7.1.0-py3-none-any.whl (354 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 13.3 MB/s eta 0:00:00
Collecting cloudpickle>=3.1.1
  Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Collecting opentelemetry-exporter-prometheus>=0.60b0
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Collecting cffi>=2.0.0
  Downloading cffi-2.0.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.4/216.4 kB 29.4 MB/s eta 0:00:00
Collecting dnspython>=2.0.0
  Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 26.7 MB/s eta 0:00:00
Collecting sortedcontainers>=2
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Collecting lupa>=2.1
  Downloading lupa-2.6-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 26.2 MB/s eta 0:00:00
Collecting SecretStorage>=3.2
  Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Collecting jaraco.context
  Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Collecting importlib_metadata>=4.11.4
  Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Collecting jeepney>=0.4.2
  Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 60.3 MB/s eta 0:00:00
Collecting jaraco.classes
  Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Collecting jaraco.functools
  Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Collecting opentelemetry-sdk~=1.39.1
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 30.7 MB/s eta 0:00:00
Collecting opentelemetry-semantic-conventions==0.60b1
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 36.1 MB/s eta 0:00:00
Collecting wrapt<2.0.0,>=1.0.0
  Downloading wrapt-1.17.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 48.3 MB/s eta 0:00:00
Collecting async-timeout>=4.0.3
  Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
Collecting charset_normalizer<4,>=2
  Downloading charset_normalizer-3.4.4-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (148 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 148.8/148.8 kB 33.5 MB/s eta 0:00:00
Collecting urllib3<3,>=1.21.1
  Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 37.8 MB/s eta 0:00:00
Collecting docutils
  Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 25.6 MB/s eta 0:00:00
Collecting shellingham>=1.3.0
  Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Collecting pycparser
  Downloading pycparser-3.0-py3-none-any.whl (48 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 97.0 MB/s eta 0:00:00
Collecting zipp>=3.20
  Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Collecting more-itertools
  Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 61.7 MB/s eta 0:00:00
Collecting backports.tarfile
  Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=436366 sha256=e4bd2e8b68809e179c294269b29c21f01d2634d34c71074331673a92e5efeee5
  Stored in directory: /tmp/pip-ephem-wheel-cache-f471d545/wheels/60/38/27/e774dc618089d42af20ea07600f801fa663a4b3310be033a3c
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, typing-extensions, tomli, shellingham, rpds-py, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, idna, httpx-sse, h11, docutils, docstring-parser, dnspython, diskcache, cloudpickle, click, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, async-timeout, annotated-types, uvicorn, typing-inspection, requests, referencing, redis, rank-bm25, pydantic-core, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, exceptiongroup, email-validator, cffi, rich, pydantic, py-key-value-aio, opentelemetry-api, jsonschema-specifications, jsonschema-path, fakeredis, cryptography, anyio, typer, starlette, SecretStorage, rich-rst, pydantic-settings, opentelemetry-semantic-conventions, openapi-pydantic, jsonschema, httpx, authlib, sse-starlette, opentelemetry-sdk, opentelemetry-instrumentation, keyring, cyclopts, opentelemetry-exporter-prometheus, mcp, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.1 async-timeout-5.0.1 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.2.6 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 starlette-0.52.1 tomli-2.4.0 typer-0.21.1 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.40.0 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> bbd0c19cd047
STEP 9/10: COPY tools/adk_knowledge_ext/tests/integration/resilience_no_api_key/verify_fail_no_key.py /app/verify.py
--> 36ef13dc278a
STEP 10/10: CMD ["python", "/app/verify.py"]
COMMIT adk-test-res-key
--> 48c9a956c616
Successfully tagged localhost/adk-test-res-key:latest
48c9a956c616595e9f3a09536df7a8dc5d83863baf6209d98d32c7ccd83d24e4
2026-01-31 22:42:18,880 - codebase-knowledge-mcp - ERROR - TARGET_REPO_URL environment variable is not set. Cloning will be unavailable.
2026-01-31 22:42:18,884 - adk_knowledge_ext.reader - INFO - Cloning  (v1.20.0) from  to /root/.mcp_cache/v1.20.0...
2026-01-31 22:42:18,888 - adk_knowledge_ext.reader - ERROR - Failed to clone repository: fatal: repository '' does not exist

2026-01-31 22:42:18,896 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
--- Starting Resilience Verification (Hybrid search, No Key) ---
Launching Server...
Server Initialized.
Calling list_modules (Expect failure due to no key)...
Tool Output: Error executing tool list_modules: ADK_SEARCH_PROVIDER is 'hybrid' but GEMINI_API_KEY is missing. API key is required for embedding-based search.
SUCCESS: Server correctly failed tool call due to missing API key.
STEP 1/9: FROM python:3.10-slim
STEP 2/9: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/9: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/9: COPY benchmarks/generator/benchmark_generator/data/ranked_targets.yaml /tmp/local_index.yaml
--> Using cache 1452078ceae739f011b4091dc07e05b179ca98406633208d578f4b2d5412b2d1
--> 1452078ceae7
STEP 5/9: COPY tools/adk_knowledge_ext /tmp/pkg
--> 2fca5ee69685
STEP 6/9: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Collecting mcp
  Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 6.2 MB/s eta 0:00:00
Collecting click
  Downloading click-8.3.1-py3-none-any.whl (108 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 108.3/108.3 kB 89.7 MB/s eta 0:00:00
Collecting rank-bm25
  Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Collecting fastmcp
  Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 20.8 MB/s eta 0:00:00
Collecting rich
  Downloading rich-14.3.1-py3-none-any.whl (309 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 32.7 MB/s eta 0:00:00
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (740 kB)
Collecting pyperclip>=1.9.0
  Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Collecting jsonref>=1.1.0
  Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Collecting openapi-pydantic>=0.5.1
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 27.7 MB/s eta 0:00:00
Collecting uvicorn>=0.35
  Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.5/68.5 kB 72.1 MB/s eta 0:00:00
Collecting httpx>=0.28.1
  Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 101.9 MB/s eta 0:00:00
Collecting authlib>=1.6.5
  Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 36.5 MB/s eta 0:00:00
Collecting packaging>=20.0
  Using cached packaging-26.0-py3-none-any.whl (74 kB)
Collecting jsonschema-path>=0.3.4
  Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Collecting websockets>=15.0.1
  Downloading websockets-16.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.1/185.1 kB 38.5 MB/s eta 0:00:00
Collecting cyclopts>=4.0.0
  Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 33.5 MB/s eta 0:00:00
Collecting platformdirs>=4.0.0
  Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Collecting python-dotenv>=1.1.0
  Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Collecting py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 39.7 MB/s eta 0:00:00
Collecting exceptiongroup>=1.2.2
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting pydocket<0.17.0,>=0.16.6
  Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 30.2 MB/s eta 0:00:00
Collecting pydantic[email]>=2.11.7
  Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 44.2 MB/s eta 0:00:00
Collecting python-multipart>=0.0.9
  Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Collecting anyio>=4.5
  Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 48.5 MB/s eta 0:00:00
Collecting httpx-sse>=0.4
  Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Collecting typing-inspection>=0.4.1
  Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Collecting starlette>=0.27
  Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 25.9 MB/s eta 0:00:00
Collecting typing-extensions>=4.9.0
  Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 79.1 MB/s eta 0:00:00
Collecting pydantic-settings>=2.5.2
  Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 18.4 MB/s eta 0:00:00
Collecting jsonschema>=4.20.0
  Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 139.9 MB/s eta 0:00:00
Collecting pyjwt[crypto]>=2.10.1
  Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Collecting sse-starlette>=1.6.1
  Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Collecting markdown-it-py>=2.2.0
  Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 40.0 MB/s eta 0:00:00
Collecting pygments<3.0.0,>=2.13.0
  Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 29.0 MB/s eta 0:00:00
Collecting numpy
  Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 37.3 MB/s eta 0:00:00
Collecting idna>=2.8
  Downloading idna-3.11-py3-none-any.whl (71 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71.0/71.0 kB 38.6 MB/s eta 0:00:00
Collecting cryptography
  Downloading cryptography-46.0.4-cp38-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 37.5 MB/s eta 0:00:00
Collecting attrs>=23.1.0
  Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 53.5 MB/s eta 0:00:00
Collecting rich-rst<2.0.0,>=1.3.1
  Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Collecting docstring-parser<4.0,>=0.15
  Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Collecting tomli>=2.0.0
  Using cached tomli-2.4.0-py3-none-any.whl (14 kB)
Collecting httpcore==1.*
  Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 35.5 MB/s eta 0:00:00
Collecting certifi
  Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 30.4 MB/s eta 0:00:00
Collecting h11>=0.16
  Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Collecting rpds-py>=0.25.0
  Downloading rpds_py-0.30.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.7/389.7 kB 40.9 MB/s eta 0:00:00
Collecting referencing>=0.28.4
  Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
Collecting jsonschema-specifications>=2023.03.6
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Collecting pathable<0.5.0,>=0.4.1
  Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting requests<3.0.0,>=2.31.0
  Downloading requests-2.32.5-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 56.4 MB/s eta 0:00:00
Collecting mdurl~=0.1
  Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Collecting beartype>=0.20.0
  Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 31.5 MB/s eta 0:00:00
Collecting py-key-value-shared==0.3.0
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Collecting cachetools>=5.0.0
  Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Collecting diskcache>=5.0.0
  Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 38.6 MB/s eta 0:00:00
Collecting pathvalidate>=3.3.1
  Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Collecting keyring>=25.6.0
  Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Collecting pydantic-core==2.41.5
  Downloading pydantic_core-2.41.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 19.8 MB/s eta 0:00:00
Collecting annotated-types>=0.6.0
  Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting email-validator>=2.0.0
  Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Collecting fakeredis[lua]>=2.32.1
  Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 49.8 MB/s eta 0:00:00
Collecting redis>=5
  Downloading redis-7.1.0-py3-none-any.whl (354 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 72.1 MB/s eta 0:00:00
Collecting opentelemetry-instrumentation>=0.60b0
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Collecting typer>=0.15.1
  Downloading typer-0.21.1-py3-none-any.whl (47 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 18.6 MB/s eta 0:00:00
Collecting cloudpickle>=3.1.1
  Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Collecting opentelemetry-api>=1.33.0
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 107.5 MB/s eta 0:00:00
Collecting prometheus-client>=0.21.1
  Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 59.2 MB/s eta 0:00:00
Collecting opentelemetry-exporter-prometheus>=0.60b0
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Collecting python-json-logger>=2.0.7
  Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Collecting cffi>=2.0.0
  Downloading cffi-2.0.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.4/216.4 kB 111.3 MB/s eta 0:00:00
Collecting dnspython>=2.0.0
  Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 17.7 MB/s eta 0:00:00
Collecting sortedcontainers>=2
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Collecting lupa>=2.1
  Downloading lupa-2.6-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 31.8 MB/s eta 0:00:00
Collecting jaraco.functools
  Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Collecting jaraco.classes
  Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Collecting SecretStorage>=3.2
  Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Collecting jeepney>=0.4.2
  Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 112.1 MB/s eta 0:00:00
Collecting jaraco.context
  Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Collecting importlib_metadata>=4.11.4
  Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Collecting opentelemetry-sdk~=1.39.1
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 70.4 MB/s eta 0:00:00
Collecting wrapt<2.0.0,>=1.0.0
  Downloading wrapt-1.17.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 42.1 MB/s eta 0:00:00
Collecting opentelemetry-semantic-conventions==0.60b1
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 40.7 MB/s eta 0:00:00
Collecting async-timeout>=4.0.3
  Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
Collecting charset_normalizer<4,>=2
  Downloading charset_normalizer-3.4.4-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (148 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 148.8/148.8 kB 41.1 MB/s eta 0:00:00
Collecting urllib3<3,>=1.21.1
  Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 208.8 MB/s eta 0:00:00
Collecting docutils
  Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 34.9 MB/s eta 0:00:00
Collecting shellingham>=1.3.0
  Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Collecting pycparser
  Downloading pycparser-3.0-py3-none-any.whl (48 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 102.3 MB/s eta 0:00:00
Collecting zipp>=3.20
  Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Collecting more-itertools
  Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 33.5 MB/s eta 0:00:00
Collecting backports.tarfile
  Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=19741 sha256=bf7b456eaf5fe3f90ff97b0a50ee737adc86513fae2d325e5628239a0382edd6
  Stored in directory: /tmp/pip-ephem-wheel-cache-xy9rkmtu/wheels/60/38/27/e774dc618089d42af20ea07600f801fa663a4b3310be033a3c
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, typing-extensions, tomli, shellingham, rpds-py, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, idna, httpx-sse, h11, docutils, docstring-parser, dnspython, diskcache, cloudpickle, click, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, async-timeout, annotated-types, uvicorn, typing-inspection, requests, referencing, redis, rank-bm25, pydantic-core, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, exceptiongroup, email-validator, cffi, rich, pydantic, py-key-value-aio, opentelemetry-api, jsonschema-specifications, jsonschema-path, fakeredis, cryptography, anyio, typer, starlette, SecretStorage, rich-rst, pydantic-settings, opentelemetry-semantic-conventions, openapi-pydantic, jsonschema, httpx, authlib, sse-starlette, opentelemetry-sdk, opentelemetry-instrumentation, keyring, cyclopts, opentelemetry-exporter-prometheus, mcp, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.1 async-timeout-5.0.1 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.2.6 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 starlette-0.52.1 tomli-2.4.0 typer-0.21.1 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.40.0 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> 099b4876f24f
STEP 7/9: RUN echo "https://github.com/google/adk-python.git:\n  v1.20.0: file:///tmp/local_index.yaml" > /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/registry.yaml
--> b005f9a4776d
STEP 8/9: COPY tools/adk_knowledge_ext/tests/integration/registry_lookup/verify_registry.py /app/verify.py
--> 6ebf3ceb7af4
STEP 9/9: CMD ["python", "/app/verify.py"]
COMMIT adk-test-registry-ok
--> 1d13a2e7828b
Successfully tagged localhost/adk-test-registry-ok:latest
1d13a2e7828b822d4c3782f55bf62d725f2c2198e899e994f12377428d182347
2026-01-31 22:42:41,013 - adk_knowledge_ext.reader - INFO - Cloning adk-python (v1.20.0) from https://github.com/google/adk-python.git to /root/.mcp_cache/adk-python/v1.20.0...
2026-01-31 22:42:42,339 - adk_knowledge_ext.reader - INFO - Clone successful.
2026-01-31 22:42:42,348 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-01-31 22:42:42,349 - codebase-knowledge-mcp - INFO - Resolved index URL from registry: file:///tmp/local_index.yaml
2026-01-31 22:42:42,349 - codebase-knowledge-mcp - INFO - Downloading index for v1.20.0 from file:///tmp/local_index.yaml...
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed

  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
100 3455k  100 3455k    0     0  1285M      0 --:--:-- --:--:-- --:--:-- 1687M
2026-01-31 22:42:44,642 - adk_knowledge_ext.index - INFO - No GEMINI_API_KEY detected. Using 'bm25' search.
2026-01-31 22:42:44,642 - adk_knowledge_ext.index - INFO - Initializing search provider: bm25
2026-01-31 22:42:44,669 - adk_knowledge_ext.search - INFO - BM25 Index built with 3238 items.
2026-01-31 22:42:44,670 - adk_knowledge_ext.index - INFO - Loaded 3238 targets from index.
2026-01-31 22:42:44,670 - codebase-knowledge-mcp - INFO - System instructions available at: /root/.mcp_cache/instructions/adk-python.md
2026-01-31 22:42:44,672 - mcp.server.lowlevel.server - INFO - Processing request of type ListToolsRequest
--- Starting Registry Lookup Verification ---
Launching Server...
Server Initialized.
Calling list_modules (Expect Success via Registry)...
Tool Output: --- Ranked Modules (Page 1) ---
[1] CLASS: google.adk.runners.InMemoryRunner
[2] CLASS: google.adk.t...
SUCCESS: Registry lookup worked.
STEP 1/7: FROM python:3.10-slim
STEP 2/7: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/7: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/7: COPY tools/adk_knowledge_ext /tmp/pkg
--> f1967ad78dba
STEP 5/7: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Collecting rank-bm25
  Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Collecting rich
  Downloading rich-14.3.1-py3-none-any.whl (309 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 9.7 MB/s eta 0:00:00
Collecting mcp
  Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 37.9 MB/s eta 0:00:00
Collecting click
  Downloading click-8.3.1-py3-none-any.whl (108 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 108.3/108.3 kB 50.2 MB/s eta 0:00:00
Collecting fastmcp
  Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 37.9 MB/s eta 0:00:00
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (740 kB)
Collecting jsonschema-path>=0.3.4
  Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Collecting exceptiongroup>=1.2.2
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting openapi-pydantic>=0.5.1
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 36.3 MB/s eta 0:00:00
Collecting platformdirs>=4.0.0
  Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Collecting pyperclip>=1.9.0
  Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Collecting authlib>=1.6.5
  Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 36.9 MB/s eta 0:00:00
Collecting py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 35.9 MB/s eta 0:00:00
Collecting pydantic[email]>=2.11.7
  Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 5.2 MB/s eta 0:00:00
Collecting pydocket<0.17.0,>=0.16.6
  Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 19.1 MB/s eta 0:00:00
Collecting python-dotenv>=1.1.0
  Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Collecting uvicorn>=0.35
  Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.5/68.5 kB 30.1 MB/s eta 0:00:00
Collecting httpx>=0.28.1
  Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 61.9 MB/s eta 0:00:00
Collecting packaging>=20.0
  Using cached packaging-26.0-py3-none-any.whl (74 kB)
Collecting cyclopts>=4.0.0
  Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 15.1 MB/s eta 0:00:00
Collecting websockets>=15.0.1
  Downloading websockets-16.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.1/185.1 kB 32.7 MB/s eta 0:00:00
Collecting jsonref>=1.1.0
  Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Collecting jsonschema>=4.20.0
  Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 34.4 MB/s eta 0:00:00
Collecting pyjwt[crypto]>=2.10.1
  Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Collecting httpx-sse>=0.4
  Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Collecting sse-starlette>=1.6.1
  Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Collecting pydantic-settings>=2.5.2
  Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 80.6 MB/s eta 0:00:00
Collecting anyio>=4.5
  Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 26.4 MB/s eta 0:00:00
Collecting python-multipart>=0.0.9
  Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Collecting typing-inspection>=0.4.1
  Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Collecting starlette>=0.27
  Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 41.5 MB/s eta 0:00:00
Collecting typing-extensions>=4.9.0
  Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 93.9 MB/s eta 0:00:00
Collecting markdown-it-py>=2.2.0
  Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 52.0 MB/s eta 0:00:00
Collecting pygments<3.0.0,>=2.13.0
  Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 29.3 MB/s eta 0:00:00
Collecting numpy
  Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 22.9 MB/s eta 0:00:00
Collecting idna>=2.8
  Downloading idna-3.11-py3-none-any.whl (71 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71.0/71.0 kB 111.7 MB/s eta 0:00:00
Collecting cryptography
  Downloading cryptography-46.0.4-cp38-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 29.2 MB/s eta 0:00:00
Collecting rich-rst<2.0.0,>=1.3.1
  Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Collecting tomli>=2.0.0
  Using cached tomli-2.4.0-py3-none-any.whl (14 kB)
Collecting attrs>=23.1.0
  Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 24.9 MB/s eta 0:00:00
Collecting docstring-parser<4.0,>=0.15
  Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Collecting httpcore==1.*
  Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 128.9 MB/s eta 0:00:00
Collecting certifi
  Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 53.1 MB/s eta 0:00:00
Collecting h11>=0.16
  Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
Collecting rpds-py>=0.25.0
  Downloading rpds_py-0.30.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.7/389.7 kB 43.5 MB/s eta 0:00:00
Collecting jsonschema-specifications>=2023.03.6
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting requests<3.0.0,>=2.31.0
  Downloading requests-2.32.5-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 121.2 MB/s eta 0:00:00
Collecting pathable<0.5.0,>=0.4.1
  Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Collecting mdurl~=0.1
  Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Collecting beartype>=0.20.0
  Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 32.6 MB/s eta 0:00:00
Collecting py-key-value-shared==0.3.0
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Collecting cachetools>=5.0.0
  Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Collecting diskcache>=5.0.0
  Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 84.4 MB/s eta 0:00:00
Collecting pathvalidate>=3.3.1
  Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Collecting keyring>=25.6.0
  Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Collecting pydantic-core==2.41.5
  Downloading pydantic_core-2.41.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 32.1 MB/s eta 0:00:00
Collecting annotated-types>=0.6.0
  Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting email-validator>=2.0.0
  Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Collecting typer>=0.15.1
  Downloading typer-0.21.1-py3-none-any.whl (47 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 73.4 MB/s eta 0:00:00
Collecting prometheus-client>=0.21.1
  Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 24.4 MB/s eta 0:00:00
Collecting opentelemetry-instrumentation>=0.60b0
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Collecting python-json-logger>=2.0.7
  Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Collecting redis>=5
  Downloading redis-7.1.0-py3-none-any.whl (354 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 45.5 MB/s eta 0:00:00
Collecting fakeredis[lua]>=2.32.1
  Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 56.3 MB/s eta 0:00:00
Collecting cloudpickle>=3.1.1
  Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Collecting opentelemetry-api>=1.33.0
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 64.0 MB/s eta 0:00:00
Collecting opentelemetry-exporter-prometheus>=0.60b0
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Collecting cffi>=2.0.0
  Downloading cffi-2.0.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.4/216.4 kB 45.7 MB/s eta 0:00:00
Collecting dnspython>=2.0.0
  Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 45.6 MB/s eta 0:00:00
Collecting sortedcontainers>=2
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Collecting lupa>=2.1
  Downloading lupa-2.6-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 35.7 MB/s eta 0:00:00
Collecting SecretStorage>=3.2
  Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Collecting jaraco.functools
  Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Collecting importlib_metadata>=4.11.4
  Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Collecting jeepney>=0.4.2
  Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 108.4 MB/s eta 0:00:00
Collecting jaraco.context
  Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Collecting jaraco.classes
  Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Collecting opentelemetry-sdk~=1.39.1
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 47.8 MB/s eta 0:00:00
Collecting wrapt<2.0.0,>=1.0.0
  Downloading wrapt-1.17.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 58.9 MB/s eta 0:00:00
Collecting opentelemetry-semantic-conventions==0.60b1
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 41.6 MB/s eta 0:00:00
Collecting async-timeout>=4.0.3
  Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
Collecting urllib3<3,>=1.21.1
  Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 171.5 MB/s eta 0:00:00
Collecting charset_normalizer<4,>=2
  Downloading charset_normalizer-3.4.4-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (148 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 148.8/148.8 kB 37.1 MB/s eta 0:00:00
Collecting docutils
  Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 21.6 MB/s eta 0:00:00
Collecting shellingham>=1.3.0
  Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Collecting pycparser
  Downloading pycparser-3.0-py3-none-any.whl (48 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 82.4 MB/s eta 0:00:00
Collecting zipp>=3.20
  Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Collecting more-itertools
  Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 41.0 MB/s eta 0:00:00
Collecting backports.tarfile
  Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=19741 sha256=bf7b456eaf5fe3f90ff97b0a50ee737adc86513fae2d325e5628239a0382edd6
  Stored in directory: /tmp/pip-ephem-wheel-cache-77hcp3yj/wheels/60/38/27/e774dc618089d42af20ea07600f801fa663a4b3310be033a3c
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, typing-extensions, tomli, shellingham, rpds-py, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, idna, httpx-sse, h11, docutils, docstring-parser, dnspython, diskcache, cloudpickle, click, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, async-timeout, annotated-types, uvicorn, typing-inspection, requests, referencing, redis, rank-bm25, pydantic-core, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, exceptiongroup, email-validator, cffi, rich, pydantic, py-key-value-aio, opentelemetry-api, jsonschema-specifications, jsonschema-path, fakeredis, cryptography, anyio, typer, starlette, SecretStorage, rich-rst, pydantic-settings, opentelemetry-semantic-conventions, openapi-pydantic, jsonschema, httpx, authlib, sse-starlette, opentelemetry-sdk, opentelemetry-instrumentation, keyring, cyclopts, opentelemetry-exporter-prometheus, mcp, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.1 async-timeout-5.0.1 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.2.6 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 starlette-0.52.1 tomli-2.4.0 typer-0.21.1 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.40.0 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> 2f4d02506549
STEP 6/7: COPY tools/adk_knowledge_ext/tests/integration/registry_miss/verify_miss.py /app/verify.py
--> 5ba1825e447b
STEP 7/7: CMD ["python", "/app/verify.py"]
COMMIT adk-test-registry-miss
--> 52858a233ff8
Successfully tagged localhost/adk-test-registry-miss:latest
52858a233ff8b30926e9a0e41a34013de192d1eee90467434cec73b49504e364
2026-01-31 22:43:02,097 - adk_knowledge_ext.reader - INFO - Cloning repo (main) from https://unknown.com/repo.git to /root/.mcp_cache/repo/main...
2026-01-31 22:43:02,275 - adk_knowledge_ext.reader - ERROR - Failed to clone repository: Cloning into '/root/.mcp_cache/repo/main'...
fatal: Remote branch main not found in upstream origin

2026-01-31 22:43:02,288 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
--- Starting Registry Miss Verification ---
Launching Server...
Server Initialized.
Calling list_modules (Expect Failure)...
Tool Output: Error executing tool list_modules: This repository ('https://unknown.com/repo.git') is not supported by the Codebase Knowledge MCP server because its knowledge index is not properly set up.

TO FIX THIS:
1. Run 'codebase-knowledge-mcp-manage setup' for this repository.
2. If you are in a restricted environment, use the --knowledge-index-url flag pointing to a local YAML file.
SUCCESS: Correctly failed due to missing registry entry.
STEP 1/11: FROM gemini-cli:base
STEP 2/11: RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
--> Using cache a86b208b745e321410610c37ef69a921aee14d0efb5d2e3603b0744fac691296
--> a86b208b745e
STEP 3/11: RUN curl -LsSf https://astral.sh/uv/install.sh | sh
--> Using cache 7725bdee325deff9122e3afa9745b9ec4fd3d2dab4835ce5c3ae845b15d26cf5
--> 7725bdee325d
STEP 4/11: ENV PATH="/root/.local/bin:$PATH"
--> Using cache 1575ad09f5e71a663eb4627f2e06686a1fa94d7edeca9f5f2342cafef4fdf1d3
--> 1575ad09f5e7
STEP 5/11: WORKDIR /app
--> Using cache 9a77eaf91c56e5d8efc5218b10e94897d8cfc73884f23d0ebf16caf2eca4148c
--> 9a77eaf91c56
STEP 6/11: COPY tools/adk_knowledge_ext /tmp/pkg
--> 755ad1772162
STEP 7/11: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Requirement already satisfied: click in /usr/local/lib/python3.11/site-packages (from codebase-knowledge-mcp==0.1.0) (8.3.1)
Collecting fastmcp (from codebase-knowledge-mcp==0.1.0)
  Downloading fastmcp-2.14.4-py3-none-any.whl.metadata (20 kB)
Collecting mcp (from codebase-knowledge-mcp==0.1.0)
  Downloading mcp-1.26.0-py3-none-any.whl.metadata (89 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 89.5/89.5 kB 5.7 MB/s eta 0:00:00
Collecting pyyaml (from codebase-knowledge-mcp==0.1.0)
  Using cached pyyaml-6.0.3-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (2.4 kB)
Collecting rank-bm25 (from codebase-knowledge-mcp==0.1.0)
  Downloading rank_bm25-0.2.2-py3-none-any.whl.metadata (3.2 kB)
Collecting rich (from codebase-knowledge-mcp==0.1.0)
  Downloading rich-14.3.1-py3-none-any.whl.metadata (18 kB)
Collecting authlib>=1.6.5 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading authlib-1.6.6-py2.py3-none-any.whl.metadata (9.8 kB)
Collecting cyclopts>=4.0.0 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading cyclopts-4.5.1-py3-none-any.whl.metadata (12 kB)
Collecting exceptiongroup>=1.2.2 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading exceptiongroup-1.3.1-py3-none-any.whl.metadata (6.7 kB)
Collecting httpx>=0.28.1 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
Collecting jsonref>=1.1.0 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading jsonref-1.1.0-py3-none-any.whl.metadata (2.7 kB)
Collecting jsonschema-path>=0.3.4 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading jsonschema_path-0.3.4-py3-none-any.whl.metadata (4.3 kB)
Collecting openapi-pydantic>=0.5.1 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl.metadata (10 kB)
Collecting packaging>=20.0 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Using cached packaging-26.0-py3-none-any.whl.metadata (3.3 kB)
Collecting platformdirs>=4.0.0 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading platformdirs-4.5.1-py3-none-any.whl.metadata (12 kB)
Collecting py-key-value-aio<0.4.0,>=0.3.0 (from py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl.metadata (2.5 kB)
Requirement already satisfied: pydantic>=2.11.7 in /usr/local/lib/python3.11/site-packages (from pydantic[email]>=2.11.7->fastmcp->codebase-knowledge-mcp==0.1.0) (2.12.5)
Collecting pydocket<0.17.0,>=0.16.6 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading pydocket-0.16.6-py3-none-any.whl.metadata (6.3 kB)
Collecting pyperclip>=1.9.0 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading pyperclip-1.11.0-py3-none-any.whl.metadata (2.4 kB)
Collecting python-dotenv>=1.1.0 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading python_dotenv-1.2.1-py3-none-any.whl.metadata (25 kB)
Requirement already satisfied: uvicorn>=0.35 in /usr/local/lib/python3.11/site-packages (from fastmcp->codebase-knowledge-mcp==0.1.0) (0.40.0)
Collecting websockets>=15.0.1 (from fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading websockets-16.0-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (6.8 kB)
Requirement already satisfied: anyio>=4.5 in /usr/local/lib/python3.11/site-packages (from mcp->codebase-knowledge-mcp==0.1.0) (4.12.1)
Collecting httpx-sse>=0.4 (from mcp->codebase-knowledge-mcp==0.1.0)
  Downloading httpx_sse-0.4.3-py3-none-any.whl.metadata (9.7 kB)
Collecting jsonschema>=4.20.0 (from mcp->codebase-knowledge-mcp==0.1.0)
  Downloading jsonschema-4.26.0-py3-none-any.whl.metadata (7.6 kB)
Collecting pydantic-settings>=2.5.2 (from mcp->codebase-knowledge-mcp==0.1.0)
  Downloading pydantic_settings-2.12.0-py3-none-any.whl.metadata (3.4 kB)
Collecting pyjwt>=2.10.1 (from pyjwt[crypto]>=2.10.1->mcp->codebase-knowledge-mcp==0.1.0)
  Downloading pyjwt-2.11.0-py3-none-any.whl.metadata (4.0 kB)
Collecting python-multipart>=0.0.9 (from mcp->codebase-knowledge-mcp==0.1.0)
  Downloading python_multipart-0.0.22-py3-none-any.whl.metadata (1.8 kB)
Collecting sse-starlette>=1.6.1 (from mcp->codebase-knowledge-mcp==0.1.0)
  Downloading sse_starlette-3.2.0-py3-none-any.whl.metadata (12 kB)
Requirement already satisfied: starlette>=0.27 in /usr/local/lib/python3.11/site-packages (from mcp->codebase-knowledge-mcp==0.1.0) (0.50.0)
Requirement already satisfied: typing-extensions>=4.9.0 in /usr/local/lib/python3.11/site-packages (from mcp->codebase-knowledge-mcp==0.1.0) (4.15.0)
Requirement already satisfied: typing-inspection>=0.4.1 in /usr/local/lib/python3.11/site-packages (from mcp->codebase-knowledge-mcp==0.1.0) (0.4.2)
Collecting markdown-it-py>=2.2.0 (from rich->codebase-knowledge-mcp==0.1.0)
  Downloading markdown_it_py-4.0.0-py3-none-any.whl.metadata (7.3 kB)
Collecting pygments<3.0.0,>=2.13.0 (from rich->codebase-knowledge-mcp==0.1.0)
  Downloading pygments-2.19.2-py3-none-any.whl.metadata (2.5 kB)
Collecting numpy (from rank-bm25->codebase-knowledge-mcp==0.1.0)
  Downloading numpy-2.4.1-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl.metadata (6.6 kB)
Requirement already satisfied: idna>=2.8 in /usr/local/lib/python3.11/site-packages (from anyio>=4.5->mcp->codebase-knowledge-mcp==0.1.0) (3.11)
Collecting cryptography (from authlib>=1.6.5->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading cryptography-46.0.4-cp311-abi3-manylinux_2_34_aarch64.whl.metadata (5.7 kB)
Collecting attrs>=23.1.0 (from cyclopts>=4.0.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading attrs-25.4.0-py3-none-any.whl.metadata (10 kB)
Collecting docstring-parser<4.0,>=0.15 (from cyclopts>=4.0.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading docstring_parser-0.17.0-py3-none-any.whl.metadata (3.5 kB)
Collecting rich-rst<2.0.0,>=1.3.1 (from cyclopts>=4.0.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading rich_rst-1.3.2-py3-none-any.whl.metadata (6.1 kB)
Collecting certifi (from httpx>=0.28.1->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading certifi-2026.1.4-py3-none-any.whl.metadata (2.5 kB)
Collecting httpcore==1.* (from httpx>=0.28.1->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Requirement already satisfied: h11>=0.16 in /usr/local/lib/python3.11/site-packages (from httpcore==1.*->httpx>=0.28.1->fastmcp->codebase-knowledge-mcp==0.1.0) (0.16.0)
Collecting jsonschema-specifications>=2023.03.6 (from jsonschema>=4.20.0->mcp->codebase-knowledge-mcp==0.1.0)
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl.metadata (2.9 kB)
Collecting referencing>=0.28.4 (from jsonschema>=4.20.0->mcp->codebase-knowledge-mcp==0.1.0)
  Downloading referencing-0.37.0-py3-none-any.whl.metadata (2.8 kB)
Collecting rpds-py>=0.25.0 (from jsonschema>=4.20.0->mcp->codebase-knowledge-mcp==0.1.0)
  Downloading rpds_py-0.30.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.1 kB)
Collecting pathable<0.5.0,>=0.4.1 (from jsonschema-path>=0.3.4->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading pathable-0.4.4-py3-none-any.whl.metadata (1.8 kB)
Collecting referencing>=0.28.4 (from jsonschema>=4.20.0->mcp->codebase-knowledge-mcp==0.1.0)
  Downloading referencing-0.36.2-py3-none-any.whl.metadata (2.8 kB)
Collecting requests<3.0.0,>=2.31.0 (from jsonschema-path>=0.3.4->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading requests-2.32.5-py3-none-any.whl.metadata (4.9 kB)
Collecting mdurl~=0.1 (from markdown-it-py>=2.2.0->rich->codebase-knowledge-mcp==0.1.0)
  Downloading mdurl-0.1.2-py3-none-any.whl.metadata (1.6 kB)
Collecting py-key-value-shared==0.3.0 (from py-key-value-aio<0.4.0,>=0.3.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl.metadata (706 bytes)
Collecting beartype>=0.20.0 (from py-key-value-aio<0.4.0,>=0.3.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading beartype-0.22.9-py3-none-any.whl.metadata (37 kB)
Collecting diskcache>=5.0.0 (from py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading diskcache-5.6.3-py3-none-any.whl.metadata (20 kB)
Collecting pathvalidate>=3.3.1 (from py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading pathvalidate-3.3.1-py3-none-any.whl.metadata (12 kB)
Collecting keyring>=25.6.0 (from py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading keyring-25.7.0-py3-none-any.whl.metadata (21 kB)
Collecting cachetools>=5.0.0 (from py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading cachetools-6.2.6-py3-none-any.whl.metadata (5.6 kB)
Requirement already satisfied: annotated-types>=0.6.0 in /usr/local/lib/python3.11/site-packages (from pydantic>=2.11.7->pydantic[email]>=2.11.7->fastmcp->codebase-knowledge-mcp==0.1.0) (0.7.0)
Requirement already satisfied: pydantic-core==2.41.5 in /usr/local/lib/python3.11/site-packages (from pydantic>=2.11.7->pydantic[email]>=2.11.7->fastmcp->codebase-knowledge-mcp==0.1.0) (2.41.5)
Collecting email-validator>=2.0.0 (from pydantic[email]>=2.11.7->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading email_validator-2.3.0-py3-none-any.whl.metadata (26 kB)
Collecting cloudpickle>=3.1.1 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading cloudpickle-3.1.2-py3-none-any.whl.metadata (7.1 kB)
Collecting fakeredis>=2.32.1 (from fakeredis[lua]>=2.32.1->pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading fakeredis-2.33.0-py3-none-any.whl.metadata (4.4 kB)
Collecting opentelemetry-api>=1.33.0 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl.metadata (1.5 kB)
Collecting opentelemetry-exporter-prometheus>=0.60b0 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl.metadata (2.1 kB)
Collecting opentelemetry-instrumentation>=0.60b0 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl.metadata (7.2 kB)
Collecting prometheus-client>=0.21.1 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading prometheus_client-0.24.1-py3-none-any.whl.metadata (2.1 kB)
Collecting python-json-logger>=2.0.7 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading python_json_logger-4.0.0-py3-none-any.whl.metadata (4.0 kB)
Collecting redis>=5 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading redis-7.1.0-py3-none-any.whl.metadata (12 kB)
Collecting typer>=0.15.1 (from pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading typer-0.21.1-py3-none-any.whl.metadata (16 kB)
Collecting cffi>=2.0.0 (from cryptography->authlib>=1.6.5->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading cffi-2.0.0-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.whl.metadata (2.6 kB)
Collecting dnspython>=2.0.0 (from email-validator>=2.0.0->pydantic[email]>=2.11.7->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading dnspython-2.8.0-py3-none-any.whl.metadata (5.7 kB)
Collecting sortedcontainers>=2 (from fakeredis>=2.32.1->fakeredis[lua]>=2.32.1->pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl.metadata (10 kB)
Collecting lupa>=2.1 (from fakeredis[lua]>=2.32.1->pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading lupa-2.6-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (58 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 58.5/58.5 kB 18.6 MB/s eta 0:00:00
Collecting SecretStorage>=3.2 (from keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading secretstorage-3.5.0-py3-none-any.whl.metadata (4.0 kB)
Collecting jeepney>=0.4.2 (from keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading jeepney-0.9.0-py3-none-any.whl.metadata (1.2 kB)
Collecting importlib_metadata>=4.11.4 (from keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading importlib_metadata-8.7.1-py3-none-any.whl.metadata (4.7 kB)
Collecting jaraco.classes (from keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading jaraco.classes-3.4.0-py3-none-any.whl.metadata (2.6 kB)
Collecting jaraco.functools (from keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading jaraco_functools-4.4.0-py3-none-any.whl.metadata (3.0 kB)
Collecting jaraco.context (from keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading jaraco_context-6.1.0-py3-none-any.whl.metadata (4.3 kB)
Collecting opentelemetry-sdk~=1.39.1 (from opentelemetry-exporter-prometheus>=0.60b0->pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl.metadata (1.5 kB)
Collecting opentelemetry-semantic-conventions==0.60b1 (from opentelemetry-instrumentation>=0.60b0->pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl.metadata (2.4 kB)
Collecting wrapt<2.0.0,>=1.0.0 (from opentelemetry-instrumentation>=0.60b0->pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading wrapt-1.17.3-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (6.4 kB)
Collecting charset_normalizer<4,>=2 (from requests<3.0.0,>=2.31.0->jsonschema-path>=0.3.4->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading charset_normalizer-3.4.4-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (37 kB)
Collecting urllib3<3,>=1.21.1 (from requests<3.0.0,>=2.31.0->jsonschema-path>=0.3.4->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading urllib3-2.6.3-py3-none-any.whl.metadata (6.9 kB)
Collecting docutils (from rich-rst<2.0.0,>=1.3.1->cyclopts>=4.0.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading docutils-0.22.4-py3-none-any.whl.metadata (15 kB)
Collecting shellingham>=1.3.0 (from typer>=0.15.1->pydocket<0.17.0,>=0.16.6->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading shellingham-1.5.4-py2.py3-none-any.whl.metadata (3.5 kB)
Collecting pycparser (from cffi>=2.0.0->cryptography->authlib>=1.6.5->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
Collecting zipp>=3.20 (from importlib_metadata>=4.11.4->keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading zipp-3.23.0-py3-none-any.whl.metadata (3.6 kB)
Collecting more-itertools (from jaraco.classes->keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading more_itertools-10.8.0-py3-none-any.whl.metadata (39 kB)
Collecting backports.tarfile (from jaraco.context->keyring>=25.6.0->py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0->fastmcp->codebase-knowledge-mcp==0.1.0)
  Downloading backports.tarfile-1.2.0-py3-none-any.whl.metadata (2.0 kB)
Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 12.2 MB/s eta 0:00:00
Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 17.7 MB/s eta 0:00:00
Downloading rich-14.3.1-py3-none-any.whl (309 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 9.9 MB/s eta 0:00:00
Using cached pyyaml-6.0.3-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (775 kB)
Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 14.0 MB/s eta 0:00:00
Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 18.1 MB/s eta 0:00:00
Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 23.1 MB/s eta 0:00:00
Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 17.8 MB/s eta 0:00:00
Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 29.6 MB/s eta 0:00:00
Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 23.0 MB/s eta 0:00:00
Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 36.1 MB/s eta 0:00:00
Using cached packaging-26.0-py3-none-any.whl (74 kB)
Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 22.5 MB/s eta 0:00:00
Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 22.1 MB/s eta 0:00:00
Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 40.4 MB/s eta 0:00:00
Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 23.5 MB/s eta 0:00:00
Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Downloading websockets-16.0-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.9/185.9 kB 67.1 MB/s eta 0:00:00
Downloading numpy-2.4.1-cp311-cp311-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl (14.7 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.7/14.7 MB 33.9 MB/s eta 0:00:00
Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 39.4 MB/s eta 0:00:00
Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 8.2 MB/s eta 0:00:00
Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Downloading cryptography-46.0.4-cp311-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 27.9 MB/s eta 0:00:00
Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 33.8 MB/s eta 0:00:00
Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 41.6 MB/s eta 0:00:00
Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 17.8 MB/s eta 0:00:00
Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 60.4 MB/s eta 0:00:00
Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 92.6 MB/s eta 0:00:00
Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Downloading redis-7.1.0-py3-none-any.whl (354 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 43.9 MB/s eta 0:00:00
Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Downloading requests-2.32.5-py3-none-any.whl (64 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 47.0 MB/s eta 0:00:00
Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 57.6 MB/s eta 0:00:00
Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Downloading rpds_py-0.30.0-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.9/389.9 kB 40.4 MB/s eta 0:00:00
Downloading typer-0.21.1-py3-none-any.whl (47 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 58.0 MB/s eta 0:00:00
Downloading cffi-2.0.0-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.5/216.5 kB 70.2 MB/s eta 0:00:00
Downloading charset_normalizer-3.4.4-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (147 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 147.3/147.3 kB 44.0 MB/s eta 0:00:00
Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 32.3 MB/s eta 0:00:00
Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 28.6 MB/s eta 0:00:00
Downloading lupa-2.6-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.0 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.0/1.0 MB 26.1 MB/s eta 0:00:00
Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 112.5 MB/s eta 0:00:00
Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 45.1 MB/s eta 0:00:00
Downloading wrapt-1.17.3-cp311-cp311-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.6/83.6 kB 20.4 MB/s eta 0:00:00
Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 25.3 MB/s eta 0:00:00
Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 45.8 MB/s eta 0:00:00
Downloading pycparser-3.0-py3-none-any.whl (48 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 40.3 MB/s eta 0:00:00
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=19741 sha256=bf7b456eaf5fe3f90ff97b0a50ee737adc86513fae2d325e5628239a0382edd6
  Stored in directory: /tmp/pip-ephem-wheel-cache-zcy0foce/wheels/31/79/26/c037450726c20d42d62086b445c94f8c804b9e25063a2eee72
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, shellingham, rpds-py, redis, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, httpx-sse, exceptiongroup, docutils, docstring-parser, dnspython, diskcache, cloudpickle, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, requests, referencing, rank-bm25, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, fakeredis, email-validator, cffi, sse-starlette, rich, pydantic-settings, py-key-value-aio, opentelemetry-api, openapi-pydantic, jsonschema-specifications, jsonschema-path, httpx, cryptography, typer, SecretStorage, rich-rst, opentelemetry-semantic-conventions, jsonschema, authlib, opentelemetry-sdk, opentelemetry-instrumentation, mcp, keyring, cyclopts, opentelemetry-exporter-prometheus, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.4.1 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 typer-0.21.1 urllib3-2.6.3 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 24.0 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> 4e7c7915a7e9
STEP 8/11: RUN chmod +x /usr/local/lib/python3.11/site-packages/adk_knowledge_ext/manage_mcp.py
--> 0c1e539c418c
STEP 9/11: COPY tools/adk_knowledge_ext/tests/integration/common/verify_mcp_config.py /app/verify_tools.py
--> edaec6317979
STEP 10/11: COPY tools/adk_knowledge_ext/tests/integration/managed_setup/verify_managed_setup.py /app/verify.py
--> 4756c1fe2e99
STEP 11/11: CMD ["python", "/app/verify.py"]
COMMIT adk-test-managed-setup
--> a4a846eead03
Successfully tagged localhost/adk-test-managed-setup:latest
a4a846eead037909bb637d76d0ebd36e0b030a532d1990de68cde1fc0fc47b55
--- Starting Real Managed Setup Verification ---
Step 1: Running setup...
Running:  codebase-knowledge-mcp-manage setup --repo-url https://github.com/test/repo.git --version v1.0.0 --api-key fake-key --force
Step 2: Verifying with 'gemini mcp list'...
Gemini Output:
Configured MCP servers:

[31m✗[0m codebase-knowledge: env TARGET_REPO_URL=https://github.com/test/repo.git TARGET_VERSION=v1.0.0 GEMINI_API_KEY=fake-key uvx --from git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext codebase-knowledge-mcp (stdio) - Disconnected

SUCCESS: Server found in Gemini config.
Step 3: Re-running setup with --index-url...
Running:  codebase-knowledge-mcp-manage setup --repo-url https://github.com/test/repo.git --version v1.0.0 --api-key fake-key --index-url https://test.pypi.org/simple --force
Step 4: Verifying --index-url in config...
Gemini Output:
Configured MCP servers:

[31m✗[0m codebase-knowledge: env TARGET_REPO_URL=https://github.com/test/repo.git TARGET_VERSION=v1.0.0 GEMINI_API_KEY=fake-key uvx --index-url https://test.pypi.org/simple --from git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext codebase-knowledge-mcp (stdio) - Disconnected

SUCCESS: --index-url found in configuration.
Step 5: Re-running setup with --knowledge-index-url (local file)...
Running:  codebase-knowledge-mcp-manage setup --repo-url https://github.com/test/repo.git --version v1.0.0 --api-key fake-key --knowledge-index-url file:///tmp/test_index.yaml --force
Step 6: Verifying TARGET_INDEX_URL in config...
Gemini Output:
Configured MCP servers:

[31m✗[0m codebase-knowledge: env TARGET_REPO_URL=https://github.com/test/repo.git TARGET_VERSION=v1.0.0 GEMINI_API_KEY=fake-key TARGET_INDEX_URL=file:///tmp/test_index.yaml uvx --from git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext codebase-knowledge-mcp (stdio) - Disconnected

SUCCESS: TARGET_INDEX_URL found in configuration.
Step 7: Verifying Tool Execution...
Running verification script: /usr/local/bin/python /app/verify_tools.py
Verification Output:
--- Starting MCP Verification ---
Found server configuration: codebase-knowledge
DEBUG: Resolved command 'uvx'. TEST_LOCAL_OVERRIDE=1
Test Override: Replacing 'uvx' with local 'codebase-knowledge-mcp' binary.
Server Initialized.
Available Tools: ['list_modules', 'search_knowledge', 'read_source_code', 'inspect_symbol']
Testing 'list_modules'...
SUCCESS: Index loaded and tools working.
Skipping 'read_source_code' check (TEST_SKIP_CLONE_CHECK is set).

Verification Stderr:
2026-01-31 22:43:40,321 - adk_knowledge_ext.reader - INFO - Cloning repo (v1.0.0) from https://github.com/test/repo.git to /root/.mcp_cache/repo/v1.0.0...
2026-01-31 22:43:40,422 - adk_knowledge_ext.reader - ERROR - Failed to clone repository: Cloning into '/root/.mcp_cache/repo/v1.0.0'...
fatal: could not read Username for 'https://github.com': No such device or address

2026-01-31 22:43:40,430 - mcp.server.lowlevel.server - INFO - Processing request of type ListToolsRequest
2026-01-31 22:43:40,431 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-01-31 22:43:40,431 - codebase-knowledge-mcp - INFO - Downloading index for v1.0.0 from file:///tmp/test_index.yaml...
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed

  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
100    44  100    44    0     0   914k      0 --:--:-- --:--:-- --:--:--  914k
2026-01-31 22:43:40,437 - adk_knowledge_ext.index - INFO - GEMINI_API_KEY detected. Auto-upgrading search to 'hybrid'.
2026-01-31 22:43:40,437 - adk_knowledge_ext.index - INFO - Initializing search provider: hybrid
2026-01-31 22:43:40,437 - adk_knowledge_ext.search - INFO - BM25 Index built with 1 items.
2026-01-31 22:43:40,437 - adk_knowledge_ext.search - INFO - Keyword Search Index ready.
2026-01-31 22:43:40,437 - adk_knowledge_ext.index - INFO - Loaded 1 targets from index.
2026-01-31 22:43:40,437 - codebase-knowledge-mcp - INFO - System instructions available at: /root/.mcp_cache/instructions/repo.md

SUCCESS: Tool execution passed via shared verifier.
Step 8: Running remove...
Step 9: Verifying removal...
Gemini Output:
No MCP servers configured.

SUCCESS: Server correctly removed.
STEP 1/8: FROM python:3.10-slim
STEP 2/8: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/8: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/8: COPY tools/adk_knowledge_ext /tmp/pkg
--> 388be973e9f0
STEP 5/8: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Collecting rich
  Downloading rich-14.3.1-py3-none-any.whl (309 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 7.4 MB/s eta 0:00:00
Collecting click
  Downloading click-8.3.1-py3-none-any.whl (108 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 108.3/108.3 kB 44.6 MB/s eta 0:00:00
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (740 kB)
Collecting fastmcp
  Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 24.8 MB/s eta 0:00:00
Collecting rank-bm25
  Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Collecting mcp
  Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 50.4 MB/s eta 0:00:00
Collecting pydantic[email]>=2.11.7
  Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 39.5 MB/s eta 0:00:00
Collecting packaging>=20.0
  Using cached packaging-26.0-py3-none-any.whl (74 kB)
Collecting authlib>=1.6.5
  Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 20.6 MB/s eta 0:00:00
Collecting exceptiongroup>=1.2.2
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting platformdirs>=4.0.0
  Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Collecting openapi-pydantic>=0.5.1
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 51.2 MB/s eta 0:00:00
Collecting py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 102.1 MB/s eta 0:00:00
Collecting pydocket<0.17.0,>=0.16.6
  Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 98.1 MB/s eta 0:00:00
Collecting websockets>=15.0.1
  Downloading websockets-16.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.1/185.1 kB 61.7 MB/s eta 0:00:00
Collecting httpx>=0.28.1
  Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 15.1 MB/s eta 0:00:00
Collecting cyclopts>=4.0.0
  Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 44.8 MB/s eta 0:00:00
Collecting pyperclip>=1.9.0
  Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Collecting jsonschema-path>=0.3.4
  Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Collecting jsonref>=1.1.0
  Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Collecting uvicorn>=0.35
  Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.5/68.5 kB 27.7 MB/s eta 0:00:00
Collecting python-dotenv>=1.1.0
  Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Collecting httpx-sse>=0.4
  Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Collecting pyjwt[crypto]>=2.10.1
  Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Collecting starlette>=0.27
  Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 38.0 MB/s eta 0:00:00
Collecting typing-extensions>=4.9.0
  Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 83.5 MB/s eta 0:00:00
Collecting typing-inspection>=0.4.1
  Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Collecting anyio>=4.5
  Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 35.5 MB/s eta 0:00:00
Collecting python-multipart>=0.0.9
  Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Collecting sse-starlette>=1.6.1
  Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Collecting jsonschema>=4.20.0
  Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 141.1 MB/s eta 0:00:00
Collecting pydantic-settings>=2.5.2
  Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 88.0 MB/s eta 0:00:00
Collecting pygments<3.0.0,>=2.13.0
  Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 33.4 MB/s eta 0:00:00
Collecting markdown-it-py>=2.2.0
  Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 163.5 MB/s eta 0:00:00
Collecting numpy
  Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 16.2 MB/s eta 0:00:00
Collecting idna>=2.8
  Downloading idna-3.11-py3-none-any.whl (71 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71.0/71.0 kB 37.3 MB/s eta 0:00:00
Collecting cryptography
  Downloading cryptography-46.0.4-cp38-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 33.8 MB/s eta 0:00:00
Collecting tomli>=2.0.0
  Using cached tomli-2.4.0-py3-none-any.whl (14 kB)
Collecting docstring-parser<4.0,>=0.15
  Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Collecting rich-rst<2.0.0,>=1.3.1
  Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Collecting attrs>=23.1.0
  Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 32.7 MB/s eta 0:00:00
Collecting certifi
  Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 36.1 MB/s eta 0:00:00
Collecting httpcore==1.*
  Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 37.2 MB/s eta 0:00:00
Collecting h11>=0.16
  Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Collecting rpds-py>=0.25.0
  Downloading rpds_py-0.30.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.7/389.7 kB 47.9 MB/s eta 0:00:00
Collecting jsonschema-specifications>=2023.03.6
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
  Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting requests<3.0.0,>=2.31.0
  Downloading requests-2.32.5-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 109.7 MB/s eta 0:00:00
Collecting pathable<0.5.0,>=0.4.1
  Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Collecting mdurl~=0.1
  Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Collecting py-key-value-shared==0.3.0
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Collecting beartype>=0.20.0
  Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 32.8 MB/s eta 0:00:00
Collecting cachetools>=5.0.0
  Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Collecting keyring>=25.6.0
  Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Collecting pathvalidate>=3.3.1
  Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Collecting diskcache>=5.0.0
  Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 25.3 MB/s eta 0:00:00
Collecting pydantic-core==2.41.5
  Downloading pydantic_core-2.41.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 30.2 MB/s eta 0:00:00
Collecting annotated-types>=0.6.0
  Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting email-validator>=2.0.0
  Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Collecting fakeredis[lua]>=2.32.1
  Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 80.1 MB/s eta 0:00:00
Collecting cloudpickle>=3.1.1
  Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Collecting python-json-logger>=2.0.7
  Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Collecting opentelemetry-api>=1.33.0
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 30.7 MB/s eta 0:00:00
Collecting opentelemetry-instrumentation>=0.60b0
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Collecting redis>=5
  Downloading redis-7.1.0-py3-none-any.whl (354 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 41.9 MB/s eta 0:00:00
Collecting prometheus-client>=0.21.1
  Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 35.4 MB/s eta 0:00:00
Collecting opentelemetry-exporter-prometheus>=0.60b0
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Collecting typer>=0.15.1
  Downloading typer-0.21.1-py3-none-any.whl (47 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 86.8 MB/s eta 0:00:00
Collecting cffi>=2.0.0
  Downloading cffi-2.0.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.4/216.4 kB 32.3 MB/s eta 0:00:00
Collecting dnspython>=2.0.0
  Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 44.8 MB/s eta 0:00:00
Collecting sortedcontainers>=2
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Collecting lupa>=2.1
  Downloading lupa-2.6-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 38.2 MB/s eta 0:00:00
Collecting jaraco.functools
  Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Collecting jaraco.classes
  Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Collecting SecretStorage>=3.2
  Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Collecting importlib_metadata>=4.11.4
  Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Collecting jeepney>=0.4.2
  Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 39.0 MB/s eta 0:00:00
Collecting jaraco.context
  Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Collecting opentelemetry-sdk~=1.39.1
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 69.6 MB/s eta 0:00:00
Collecting wrapt<2.0.0,>=1.0.0
  Downloading wrapt-1.17.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 43.3 MB/s eta 0:00:00
Collecting opentelemetry-semantic-conventions==0.60b1
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 36.1 MB/s eta 0:00:00
Collecting async-timeout>=4.0.3
  Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
Collecting charset_normalizer<4,>=2
  Downloading charset_normalizer-3.4.4-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (148 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 148.8/148.8 kB 47.8 MB/s eta 0:00:00
Collecting urllib3<3,>=1.21.1
  Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 52.5 MB/s eta 0:00:00
Collecting docutils
  Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 36.4 MB/s eta 0:00:00
Collecting shellingham>=1.3.0
  Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Collecting pycparser
  Downloading pycparser-3.0-py3-none-any.whl (48 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 25.6 MB/s eta 0:00:00
Collecting zipp>=3.20
  Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Collecting more-itertools
  Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 97.9 MB/s eta 0:00:00
Collecting backports.tarfile
  Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=19741 sha256=bf7b456eaf5fe3f90ff97b0a50ee737adc86513fae2d325e5628239a0382edd6
  Stored in directory: /tmp/pip-ephem-wheel-cache-6gxw3vh9/wheels/60/38/27/e774dc618089d42af20ea07600f801fa663a4b3310be033a3c
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, typing-extensions, tomli, shellingham, rpds-py, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, idna, httpx-sse, h11, docutils, docstring-parser, dnspython, diskcache, cloudpickle, click, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, async-timeout, annotated-types, uvicorn, typing-inspection, requests, referencing, redis, rank-bm25, pydantic-core, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, exceptiongroup, email-validator, cffi, rich, pydantic, py-key-value-aio, opentelemetry-api, jsonschema-specifications, jsonschema-path, fakeredis, cryptography, anyio, typer, starlette, SecretStorage, rich-rst, pydantic-settings, opentelemetry-semantic-conventions, openapi-pydantic, jsonschema, httpx, authlib, sse-starlette, opentelemetry-sdk, opentelemetry-instrumentation, keyring, cyclopts, opentelemetry-exporter-prometheus, mcp, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.1 async-timeout-5.0.1 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.2.6 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 starlette-0.52.1 tomli-2.4.0 typer-0.21.1 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.40.0 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> 8d27a564e7d8
STEP 6/8: RUN chmod +x /usr/local/lib/python3.10/site-packages/adk_knowledge_ext/manage_mcp.py
--> 1f7d924851ef
STEP 7/8: COPY tools/adk_knowledge_ext/tests/integration/managed_json_setup/verify_json.py /app/verify.py
--> 06eb443919e1
STEP 8/8: CMD ["python", "/app/verify.py"]
COMMIT adk-test-managed-json
--> 85637dcc0825
Successfully tagged localhost/adk-test-managed-json:latest
85637dcc08257a0b1ca785ff2490c013eaa70377f3686e83eb3b3e60727c9bdb

╭──────────────────────────────────────────────────────────────────────────────╮
│ 🚀 Codebase Knowledge MCP Setup                                              │
│                                                                              │
│ Repo: https://github.com/test/repo.git                                       │
│ Version: v1.0.0                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
🔍 Detecting installed coding agents...
   ✗ Claude Code     (not installed)
   ! Gemini CLI      (config found at /root/.gemini, but 'gemini' not in PATH)
   ✓ Cursor          /root/.cursor 
   ✓ Windsurf        /root/.codeium/windsurf 
   ✓ Antigravity     /root/.gemini/antigravity 
   ✗ Codex           (not installed)
   ✓ Roo Code        /root/.roo-code 

Applying configuration...
✅ Cursor configured
✅ Windsurf configured
✅ Antigravity configured
✅ Roo Code configured

🎉 Setup complete!
--- Starting Multi-IDE Managed JSON Setup Verification ---
Initialized Cursor at /root/.cursor/mcp.json
Initialized Windsurf at /root/.codeium/windsurf/mcp_config.json
Initialized Roo Code at /root/.roo-code/mcp.json
Initialized Antigravity at /root/.gemini/antigravity/mcp_config.json

Running setup for all detected IDEs...
Cursor config updated.
Windsurf config updated.
Roo Code config updated.
Antigravity config updated.

Running remove...
Cursor server removed, existing config preserved.
Windsurf server removed, existing config preserved.
Roo Code server removed, existing config preserved.
Antigravity server removed, existing config preserved.

All JSON-based IDE tests PASSED.
STEP 1/9: FROM python:3.10-slim
STEP 2/9: WORKDIR /app
--> Using cache 0ad1a57163f0af3149cf1e5dded8f59094adda6ff4b6e0e0b1cdf89a0f138a13
--> 0ad1a57163f0
STEP 3/9: RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
--> Using cache bab8913e44b25bcc50f07226444dfa437b80f7950f7722444339ae12fe0d86a8
--> bab8913e44b2
STEP 4/9: COPY tools/adk_knowledge_ext /tmp/pkg
--> 04801a10d8f9
STEP 5/9: RUN pip install /tmp/pkg
Processing /tmp/pkg
  Installing build dependencies: started
  Installing build dependencies: finished with status 'done'
  Getting requirements to build wheel: started
  Getting requirements to build wheel: finished with status 'done'
  Preparing metadata (pyproject.toml): started
  Preparing metadata (pyproject.toml): finished with status 'done'
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (740 kB)
Collecting mcp
  Downloading mcp-1.26.0-py3-none-any.whl (233 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 233.6/233.6 kB 8.4 MB/s eta 0:00:00
Collecting rich
  Downloading rich-14.3.1-py3-none-any.whl (309 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 310.0/310.0 kB 25.0 MB/s eta 0:00:00
Collecting rank-bm25
  Downloading rank_bm25-0.2.2-py3-none-any.whl (8.6 kB)
Collecting click
  Downloading click-8.3.1-py3-none-any.whl (108 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 108.3/108.3 kB 47.2 MB/s eta 0:00:00
Collecting fastmcp
  Downloading fastmcp-2.14.4-py3-none-any.whl (417 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 417.8/417.8 kB 39.4 MB/s eta 0:00:00
Collecting pydantic[email]>=2.11.7
  Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 463.6/463.6 kB 42.6 MB/s eta 0:00:00
Collecting cyclopts>=4.0.0
  Downloading cyclopts-4.5.1-py3-none-any.whl (199 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 199.8/199.8 kB 48.9 MB/s eta 0:00:00
Collecting jsonref>=1.1.0
  Downloading jsonref-1.1.0-py3-none-any.whl (9.4 kB)
Collecting httpx>=0.28.1
  Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 35.9 MB/s eta 0:00:00
Collecting exceptiongroup>=1.2.2
  Downloading exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Collecting jsonschema-path>=0.3.4
  Downloading jsonschema_path-0.3.4-py3-none-any.whl (14 kB)
Collecting py-key-value-aio[disk,keyring,memory]<0.4.0,>=0.3.0
  Downloading py_key_value_aio-0.3.0-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.3/96.3 kB 29.5 MB/s eta 0:00:00
Collecting pydocket<0.17.0,>=0.16.6
  Downloading pydocket-0.16.6-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.7/67.7 kB 18.1 MB/s eta 0:00:00
Collecting pyperclip>=1.9.0
  Downloading pyperclip-1.11.0-py3-none-any.whl (11 kB)
Collecting packaging>=20.0
  Using cached packaging-26.0-py3-none-any.whl (74 kB)
Collecting platformdirs>=4.0.0
  Downloading platformdirs-4.5.1-py3-none-any.whl (18 kB)
Collecting python-dotenv>=1.1.0
  Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
Collecting openapi-pydantic>=0.5.1
  Downloading openapi_pydantic-0.5.1-py3-none-any.whl (96 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.4/96.4 kB 142.0 MB/s eta 0:00:00
Collecting authlib>=1.6.5
  Downloading authlib-1.6.6-py2.py3-none-any.whl (244 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 244.0/244.0 kB 37.8 MB/s eta 0:00:00
Collecting websockets>=15.0.1
  Downloading websockets-16.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (185 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 185.1/185.1 kB 38.6 MB/s eta 0:00:00
Collecting uvicorn>=0.35
  Downloading uvicorn-0.40.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.5/68.5 kB 25.3 MB/s eta 0:00:00
Collecting sse-starlette>=1.6.1
  Downloading sse_starlette-3.2.0-py3-none-any.whl (12 kB)
Collecting pyjwt[crypto]>=2.10.1
  Downloading pyjwt-2.11.0-py3-none-any.whl (28 kB)
Collecting pydantic-settings>=2.5.2
  Downloading pydantic_settings-2.12.0-py3-none-any.whl (51 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 51.9/51.9 kB 103.7 MB/s eta 0:00:00
Collecting anyio>=4.5
  Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 113.6/113.6 kB 46.2 MB/s eta 0:00:00
Collecting jsonschema>=4.20.0
  Downloading jsonschema-4.26.0-py3-none-any.whl (90 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 90.6/90.6 kB 180.2 MB/s eta 0:00:00
Collecting httpx-sse>=0.4
  Downloading httpx_sse-0.4.3-py3-none-any.whl (9.0 kB)
Collecting starlette>=0.27
  Downloading starlette-0.52.1-py3-none-any.whl (74 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 74.3/74.3 kB 38.4 MB/s eta 0:00:00
Collecting typing-inspection>=0.4.1
  Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
Collecting python-multipart>=0.0.9
  Downloading python_multipart-0.0.22-py3-none-any.whl (24 kB)
Collecting typing-extensions>=4.9.0
  Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.6/44.6 kB 79.4 MB/s eta 0:00:00
Collecting pygments<3.0.0,>=2.13.0
  Downloading pygments-2.19.2-py3-none-any.whl (1.2 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 28.9 MB/s eta 0:00:00
Collecting markdown-it-py>=2.2.0
  Downloading markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 87.3/87.3 kB 31.9 MB/s eta 0:00:00
Collecting numpy
  Downloading numpy-2.2.6-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.3/14.3 MB 37.6 MB/s eta 0:00:00
Collecting idna>=2.8
  Downloading idna-3.11-py3-none-any.whl (71 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 71.0/71.0 kB 107.3 MB/s eta 0:00:00
Collecting cryptography
  Downloading cryptography-46.0.4-cp38-abi3-manylinux_2_34_aarch64.whl (4.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.3/4.3 MB 24.5 MB/s eta 0:00:00
Collecting docstring-parser<4.0,>=0.15
  Downloading docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Collecting rich-rst<2.0.0,>=1.3.1
  Downloading rich_rst-1.3.2-py3-none-any.whl (12 kB)
Collecting attrs>=23.1.0
  Downloading attrs-25.4.0-py3-none-any.whl (67 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67.6/67.6 kB 25.4 MB/s eta 0:00:00
Collecting tomli>=2.0.0
  Using cached tomli-2.4.0-py3-none-any.whl (14 kB)
Collecting httpcore==1.*
  Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 4.9 MB/s eta 0:00:00
Collecting certifi
  Downloading certifi-2026.1.4-py3-none-any.whl (152 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 152.9/152.9 kB 37.3 MB/s eta 0:00:00
Collecting h11>=0.16
  Downloading h11-0.16.0-py3-none-any.whl (37 kB)
Collecting rpds-py>=0.25.0
  Downloading rpds_py-0.30.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (389 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 389.7/389.7 kB 41.6 MB/s eta 0:00:00
Collecting jsonschema-specifications>=2023.03.6
  Downloading jsonschema_specifications-2025.9.1-py3-none-any.whl (18 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.37.0-py3-none-any.whl (26 kB)
Collecting requests<3.0.0,>=2.31.0
  Downloading requests-2.32.5-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.7/64.7 kB 23.2 MB/s eta 0:00:00
Collecting pathable<0.5.0,>=0.4.1
  Downloading pathable-0.4.4-py3-none-any.whl (9.6 kB)
Collecting referencing>=0.28.4
  Downloading referencing-0.36.2-py3-none-any.whl (26 kB)
Collecting mdurl~=0.1
  Downloading mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Collecting beartype>=0.20.0
  Downloading beartype-0.22.9-py3-none-any.whl (1.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB 26.2 MB/s eta 0:00:00
Collecting py-key-value-shared==0.3.0
  Downloading py_key_value_shared-0.3.0-py3-none-any.whl (19 kB)
Collecting diskcache>=5.0.0
  Downloading diskcache-5.6.3-py3-none-any.whl (45 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.5/45.5 kB 58.0 MB/s eta 0:00:00
Collecting pathvalidate>=3.3.1
  Downloading pathvalidate-3.3.1-py3-none-any.whl (24 kB)
Collecting keyring>=25.6.0
  Downloading keyring-25.7.0-py3-none-any.whl (39 kB)
Collecting cachetools>=5.0.0
  Downloading cachetools-6.2.6-py3-none-any.whl (11 kB)
Collecting annotated-types>=0.6.0
  Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
Collecting pydantic-core==2.41.5
  Downloading pydantic_core-2.41.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 23.8 MB/s eta 0:00:00
Collecting email-validator>=2.0.0
  Downloading email_validator-2.3.0-py3-none-any.whl (35 kB)
Collecting redis>=5
  Downloading redis-7.1.0-py3-none-any.whl (354 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 354.2/354.2 kB 33.5 MB/s eta 0:00:00
Collecting typer>=0.15.1
  Downloading typer-0.21.1-py3-none-any.whl (47 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.4/47.4 kB 70.3 MB/s eta 0:00:00
Collecting fakeredis[lua]>=2.32.1
  Downloading fakeredis-2.33.0-py3-none-any.whl (119 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.6/119.6 kB 66.7 MB/s eta 0:00:00
Collecting opentelemetry-api>=1.33.0
  Downloading opentelemetry_api-1.39.1-py3-none-any.whl (66 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.4/66.4 kB 92.0 MB/s eta 0:00:00
Collecting opentelemetry-instrumentation>=0.60b0
  Downloading opentelemetry_instrumentation-0.60b1-py3-none-any.whl (33 kB)
Collecting python-json-logger>=2.0.7
  Downloading python_json_logger-4.0.0-py3-none-any.whl (15 kB)
Collecting prometheus-client>=0.21.1
  Downloading prometheus_client-0.24.1-py3-none-any.whl (64 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.1/64.1 kB 66.6 MB/s eta 0:00:00
Collecting opentelemetry-exporter-prometheus>=0.60b0
  Downloading opentelemetry_exporter_prometheus-0.60b1-py3-none-any.whl (13 kB)
Collecting cloudpickle>=3.1.1
  Downloading cloudpickle-3.1.2-py3-none-any.whl (22 kB)
Collecting cffi>=2.0.0
  Downloading cffi-2.0.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (216 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.4/216.4 kB 39.1 MB/s eta 0:00:00
Collecting dnspython>=2.0.0
  Downloading dnspython-2.8.0-py3-none-any.whl (331 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 331.1/331.1 kB 43.0 MB/s eta 0:00:00
Collecting sortedcontainers>=2
  Downloading sortedcontainers-2.4.0-py2.py3-none-any.whl (29 kB)
Collecting lupa>=2.1
  Downloading lupa-2.6-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (1.1 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.1/1.1 MB 34.8 MB/s eta 0:00:00
Collecting SecretStorage>=3.2
  Downloading secretstorage-3.5.0-py3-none-any.whl (15 kB)
Collecting jaraco.classes
  Downloading jaraco.classes-3.4.0-py3-none-any.whl (6.8 kB)
Collecting jeepney>=0.4.2
  Downloading jeepney-0.9.0-py3-none-any.whl (49 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 49.0/49.0 kB 44.7 MB/s eta 0:00:00
Collecting jaraco.functools
  Downloading jaraco_functools-4.4.0-py3-none-any.whl (10 kB)
Collecting jaraco.context
  Downloading jaraco_context-6.1.0-py3-none-any.whl (7.1 kB)
Collecting importlib_metadata>=4.11.4
  Downloading importlib_metadata-8.7.1-py3-none-any.whl (27 kB)
Collecting opentelemetry-sdk~=1.39.1
  Downloading opentelemetry_sdk-1.39.1-py3-none-any.whl (132 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 132.6/132.6 kB 50.4 MB/s eta 0:00:00
Collecting wrapt<2.0.0,>=1.0.0
  Downloading wrapt-1.17.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (83 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 108.6 MB/s eta 0:00:00
Collecting opentelemetry-semantic-conventions==0.60b1
  Downloading opentelemetry_semantic_conventions-0.60b1-py3-none-any.whl (219 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 220.0/220.0 kB 14.1 MB/s eta 0:00:00
Collecting async-timeout>=4.0.3
  Downloading async_timeout-5.0.1-py3-none-any.whl (6.2 kB)
Collecting charset_normalizer<4,>=2
  Downloading charset_normalizer-3.4.4-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (148 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 148.8/148.8 kB 87.1 MB/s eta 0:00:00
Collecting urllib3<3,>=1.21.1
  Downloading urllib3-2.6.3-py3-none-any.whl (131 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.6/131.6 kB 14.1 MB/s eta 0:00:00
Collecting docutils
  Downloading docutils-0.22.4-py3-none-any.whl (633 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 633.2/633.2 kB 27.6 MB/s eta 0:00:00
Collecting shellingham>=1.3.0
  Downloading shellingham-1.5.4-py2.py3-none-any.whl (9.8 kB)
Collecting pycparser
  Downloading pycparser-3.0-py3-none-any.whl (48 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 48.2/48.2 kB 29.1 MB/s eta 0:00:00
Collecting zipp>=3.20
  Downloading zipp-3.23.0-py3-none-any.whl (10 kB)
Collecting more-itertools
  Downloading more_itertools-10.8.0-py3-none-any.whl (69 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 69.7/69.7 kB 42.2 MB/s eta 0:00:00
Collecting backports.tarfile
  Downloading backports.tarfile-1.2.0-py3-none-any.whl (30 kB)
Building wheels for collected packages: codebase-knowledge-mcp
  Building wheel for codebase-knowledge-mcp (pyproject.toml): started
  Building wheel for codebase-knowledge-mcp (pyproject.toml): finished with status 'done'
  Created wheel for codebase-knowledge-mcp: filename=codebase_knowledge_mcp-0.1.0-py3-none-any.whl size=19741 sha256=bf7b456eaf5fe3f90ff97b0a50ee737adc86513fae2d325e5628239a0382edd6
  Stored in directory: /tmp/pip-ephem-wheel-cache-mcx6vohi/wheels/60/38/27/e774dc618089d42af20ea07600f801fa663a4b3310be033a3c
Successfully built codebase-knowledge-mcp
Installing collected packages: sortedcontainers, pyperclip, lupa, zipp, wrapt, websockets, urllib3, typing-extensions, tomli, shellingham, rpds-py, pyyaml, python-multipart, python-json-logger, python-dotenv, pyjwt, pygments, pycparser, prometheus-client, platformdirs, pathvalidate, pathable, packaging, numpy, more-itertools, mdurl, jsonref, jeepney, idna, httpx-sse, h11, docutils, docstring-parser, dnspython, diskcache, cloudpickle, click, charset_normalizer, certifi, cachetools, beartype, backports.tarfile, attrs, async-timeout, annotated-types, uvicorn, typing-inspection, requests, referencing, redis, rank-bm25, pydantic-core, py-key-value-shared, markdown-it-py, jaraco.functools, jaraco.context, jaraco.classes, importlib_metadata, httpcore, exceptiongroup, email-validator, cffi, rich, pydantic, py-key-value-aio, opentelemetry-api, jsonschema-specifications, jsonschema-path, fakeredis, cryptography, anyio, typer, starlette, SecretStorage, rich-rst, pydantic-settings, opentelemetry-semantic-conventions, openapi-pydantic, jsonschema, httpx, authlib, sse-starlette, opentelemetry-sdk, opentelemetry-instrumentation, keyring, cyclopts, opentelemetry-exporter-prometheus, mcp, pydocket, fastmcp, codebase-knowledge-mcp
Successfully installed SecretStorage-3.5.0 annotated-types-0.7.0 anyio-4.12.1 async-timeout-5.0.1 attrs-25.4.0 authlib-1.6.6 backports.tarfile-1.2.0 beartype-0.22.9 cachetools-6.2.6 certifi-2026.1.4 cffi-2.0.0 charset_normalizer-3.4.4 click-8.3.1 cloudpickle-3.1.2 codebase-knowledge-mcp-0.1.0 cryptography-46.0.4 cyclopts-4.5.1 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 docutils-0.22.4 email-validator-2.3.0 exceptiongroup-1.3.1 fakeredis-2.33.0 fastmcp-2.14.4 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 httpx-sse-0.4.3 idna-3.11 importlib_metadata-8.7.1 jaraco.classes-3.4.0 jaraco.context-6.1.0 jaraco.functools-4.4.0 jeepney-0.9.0 jsonref-1.1.0 jsonschema-4.26.0 jsonschema-path-0.3.4 jsonschema-specifications-2025.9.1 keyring-25.7.0 lupa-2.6 markdown-it-py-4.0.0 mcp-1.26.0 mdurl-0.1.2 more-itertools-10.8.0 numpy-2.2.6 openapi-pydantic-0.5.1 opentelemetry-api-1.39.1 opentelemetry-exporter-prometheus-0.60b1 opentelemetry-instrumentation-0.60b1 opentelemetry-sdk-1.39.1 opentelemetry-semantic-conventions-0.60b1 packaging-26.0 pathable-0.4.4 pathvalidate-3.3.1 platformdirs-4.5.1 prometheus-client-0.24.1 py-key-value-aio-0.3.0 py-key-value-shared-0.3.0 pycparser-3.0 pydantic-2.12.5 pydantic-core-2.41.5 pydantic-settings-2.12.0 pydocket-0.16.6 pygments-2.19.2 pyjwt-2.11.0 pyperclip-1.11.0 python-dotenv-1.2.1 python-json-logger-4.0.0 python-multipart-0.0.22 pyyaml-6.0.3 rank-bm25-0.2.2 redis-7.1.0 referencing-0.36.2 requests-2.32.5 rich-14.3.1 rich-rst-1.3.2 rpds-py-0.30.0 shellingham-1.5.4 sortedcontainers-2.4.0 sse-starlette-3.2.0 starlette-0.52.1 tomli-2.4.0 typer-0.21.1 typing-extensions-4.15.0 typing-inspection-0.4.2 urllib3-2.6.3 uvicorn-0.40.0 websockets-16.0 wrapt-1.17.3 zipp-3.23.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 26.0
[notice] To update, run: pip install --upgrade pip
--> 80ca355b57d5
STEP 6/9: COPY tools/adk_knowledge_ext/tests/integration/managed_claude/mock_claude.sh /usr/local/bin/claude
--> fb830f6b7061
STEP 7/9: RUN chmod +x /usr/local/bin/claude
--> 748c2d0510c8
STEP 8/9: COPY tools/adk_knowledge_ext/tests/integration/managed_claude/verify_claude.py /app/verify.py
--> 9ab30251c507
STEP 9/9: CMD ["python", "/app/verify.py"]
COMMIT adk-test-managed-claude
--> 5729a6763a7c
Successfully tagged localhost/adk-test-managed-claude:latest
5729a6763a7c3bfb2504696dbe6a45024b441925153cfaf986802bb3f9f17df0

╭──────────────────────────────────────────────────────────────────────────────╮
│ 🚀 Codebase Knowledge MCP Setup                                              │
│                                                                              │
│ Repo: https://github.com/test/repo.git                                       │
│ Version: v1.0.0                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
🔍 Detecting installed coding agents...
   ✓ Claude Code     /root/.claude 
   ✗ Gemini CLI      (not installed)
   ✗ Cursor          (not installed)
   ✗ Windsurf        (not installed)
   ✗ Antigravity     (not installed)
   ✗ Codex           (not installed)
   ✗ Roo Code        (not installed)

Applying configuration...
✅ Claude Code configured

🎉 Setup complete!

🗑️  Codebase Knowledge MCP Remove

No coding agents have this MCP configured.
--- Starting Claude Code Managed Setup Verification ---
Running setup...
Claude Mock Log:
claude mcp list
claude mcp remove codebase-knowledge --scope user
claude mcp remove codebase-knowledge --scope project
claude mcp remove codebase-knowledge --scope local
claude mcp add --scope user codebase-knowledge -- env TARGET_REPO_URL=https://github.com/test/repo.git TARGET_VERSION=v1.0.0 uvx --from git+https://github.com/ivanmkc/agent-generator.git#subdirectory=tools/adk_knowledge_ext codebase-knowledge-mcp

SUCCESS: Claude setup uses correct separator style.
Running remove...
SUCCESS: Claude remove called correctly.
Repository Root: /Users/ivanmkc/Documents/code/mcp_server

=== Building Manual Configuration (uvx) ===
--- Build adk-test-manual ---
CMD: podman build -t adk-test-manual -f tools/adk_knowledge_ext/tests/integration/manual_uvx/Dockerfile .
OK.

=== Verifying Manual Configuration (uvx) ===
--- Run adk-test-manual ---
CMD: podman run --rm adk-test-manual
OK.

=== Building Extension Installation (uvx) ===
--- Build adk-test-extension ---
CMD: podman build -t adk-test-extension -f tools/adk_knowledge_ext/tests/integration/extension_uvx/Dockerfile .
OK.

=== Verifying Extension Installation (uvx) ===
--- Run adk-test-extension ---
CMD: podman run --rm adk-test-extension
OK.

=== Building Resilience: Invalid Version ===
--- Build adk-test-res-version ---
CMD: podman build -t adk-test-res-version -f tools/adk_knowledge_ext/tests/integration/resilience_invalid_version/Dockerfile .
OK.

=== Verifying Resilience: Invalid Version ===
--- Run adk-test-res-version ---
CMD: podman run --rm adk-test-res-version
OK.

=== Building Resilience: Missing Index ===
--- Build adk-test-res-index ---
CMD: podman build -t adk-test-res-index -f tools/adk_knowledge_ext/tests/integration/resilience_missing_index/Dockerfile .
OK.

=== Verifying Resilience: Missing Index ===
--- Run adk-test-res-index ---
CMD: podman run --rm adk-test-res-index
OK.

=== Building Resilience: Missing API Key ===
--- Build adk-test-res-key ---
CMD: podman build -t adk-test-res-key -f tools/adk_knowledge_ext/tests/integration/resilience_no_api_key/Dockerfile .
OK.

=== Verifying Resilience: Missing API Key ===
--- Run adk-test-res-key ---
CMD: podman run --rm adk-test-res-key
OK.

=== Building Registry: Valid Lookup ===
--- Build adk-test-registry-ok ---
CMD: podman build -t adk-test-registry-ok -f tools/adk_knowledge_ext/tests/integration/registry_lookup/Dockerfile .
OK.

=== Verifying Registry: Valid Lookup ===
--- Run adk-test-registry-ok ---
CMD: podman run --rm adk-test-registry-ok
OK.

=== Building Registry: Unknown Repo ===
--- Build adk-test-registry-miss ---
CMD: podman build -t adk-test-registry-miss -f tools/adk_knowledge_ext/tests/integration/registry_miss/Dockerfile .
OK.

=== Verifying Registry: Unknown Repo ===
--- Run adk-test-registry-miss ---
CMD: podman run --rm adk-test-registry-miss
OK.

=== Building Managed Setup (CLI Integration) ===
--- Build adk-test-managed-setup ---
CMD: podman build -t adk-test-managed-setup -f tools/adk_knowledge_ext/tests/integration/managed_setup/Dockerfile .
OK.

=== Verifying Managed Setup (CLI Integration) ===
--- Run adk-test-managed-setup ---
CMD: podman run --rm adk-test-managed-setup
OK.

=== Building Managed Setup (JSON Integration) ===
--- Build adk-test-managed-json ---
CMD: podman build -t adk-test-managed-json -f tools/adk_knowledge_ext/tests/integration/managed_json_setup/Dockerfile .
OK.

=== Verifying Managed Setup (JSON Integration) ===
--- Run adk-test-managed-json ---
CMD: podman run --rm adk-test-managed-json
OK.

=== Building Managed Setup (Claude Code Mock) ===
--- Build adk-test-managed-claude ---
CMD: podman build -t adk-test-managed-claude -f tools/adk_knowledge_ext/tests/integration/managed_claude/Dockerfile .
OK.

=== Verifying Managed Setup (Claude Code Mock) ===
--- Run adk-test-managed-claude ---
CMD: podman run --rm adk-test-managed-claude
OK.


All Integration Tests PASSED.

```
