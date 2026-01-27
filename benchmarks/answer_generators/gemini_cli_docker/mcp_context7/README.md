# MCP Context7

## Core Philosophy
Integrates the Context7 semantic search engine as a Model Context Protocol (MCP) server, enabling the Gemini CLI to perform high-fidelity semantic retrieval over large codebases or documentation sets.

## Topology
MCP Server Integration

## Key Tool Chain
- Context7 (Semantic Search Engine)
- MCP (Model Context Protocol)
- Gemini CLI

## Architecture Overview
This image extends the base Gemini CLI by launching a sidecar MCP server (`context7-server`). The CLI is configured to route relevant "search" or "context" requests to this server via the standardized MCP interface, providing a plug-and-play RAG capability without modifying the core CLI logic.
