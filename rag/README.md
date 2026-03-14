# Phase 3: Knowledge Synthesis (RAG & LLM Brain)

## Purpose
This directory houses the logic for translating natural language user queries into executable UI pathways using Retrieval-Augmented Generation (RAG). This phase uses **LangChain** for orchestration.

## Mechanism
1. **Embedding:** User manuals and project documentation are embedded into a vector database using LangChain's document loaders and embedding models.
2. **Retrieval:** When a user asks a question, the LLM, augmented by LangChain retrievers, fetches relevant instructions from the embedded documentation.
3. **Translation & Routing:** LangChain agents/chains translate the user's intent and query the UI Knowledge Graph (Phase 2) to find the precise sequence of actions (clicks, inputs) required to execute the requested task on the target website.
