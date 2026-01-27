# Trivial Answer Generator

## Core Philosophy
A minimal, deterministic generator used for testing the benchmark infrastructure itself. It provides predictable, "trivial" responses to ensure the harness is correctly capturing and scoring results.

## Topology
Mock Generator

## Architecture Overview
The Trivial Answer Generator bypasses all LLM logic and retrieval. It returns hardcoded or simple algorithmic responses (e.g., "Hello World" or the first option in a multiple-choice question). It is used to verify that the `BenchmarkRunner` and `Analysis` pipelines are functioning correctly without consuming API tokens.
