# Phase 2: UI Knowledge Graph

## Purpose
This directory contains the code responsible for storing and managing the crawler's findings in a structured, queryable format, specifically using **Neo4j**.

## Structure
The knowledge graph uses a standardized data schema tailored for graph databases (Neo4j):

* **Nodes (States):** Represent what the user sees on a page (e.g., "Main Catalogue Page", "Filter Modal Open"). Nodes contain a `capabilities` object detailing what can be done in that state, along with `available_elements`.
* **Edges (Actions):** Represent the exact interactions required to move between nodes (e.g., an `interaction_type` like "click", targeting a specific CSS selector or element ID).

## Usage

### Prerequisites

Make sure Neo4j is running. Start it with the production Docker Compose profile from the project root:

```bash
docker compose --profile production up neo4j -d
```

Then install dependencies inside this directory:

```bash
cd graph
npm install
```

### Initialise the schema

Creates uniqueness constraints and indexes in Neo4j. Safe to re-run — all operations use `IF NOT EXISTS`.

```bash
npm run init-schema
```

Environment variables (all optional, shown with their defaults):

| Variable        | Default                  | Description              |
|-----------------|--------------------------|--------------------------|
| `NEO4J_URI`     | `bolt://localhost:7687`  | Neo4j Bolt endpoint      |
| `NEO4J_USER`    | `neo4j`                  | Neo4j username           |
| `NEO4J_PASSWORD`| `password`               | Neo4j password           |

### Import graph data

Reads the JSON file produced by the crawler and imports all nodes and relationships into Neo4j.

```bash
npm run import
```

Additional environment variable:

| Variable          | Default                          | Description                          |
|-------------------|----------------------------------|--------------------------------------|
| `GRAPH_JSON_PATH` | `../crawler/output/graph.json`   | Path to the crawler's output file    |

Example with custom paths:

```bash
GRAPH_JSON_PATH=/tmp/my-graph.json NEO4J_URI=bolt://localhost:7687 npm run import
```

### Query helpers

`scripts/queries.js` exports the following functions for use by the RAG service:

- `findStateByUrl(session, url)` — fetch a `UIState` node by its URL.
- `findPathBetweenStates(session, startNodeId, endNodeId)` — shortest directed path between two states.
- `getStateCapabilities(session, nodeId)` — retrieve capabilities and available elements for a state.
- `searchStatesByDescription(session, keyword)` — case-insensitive substring search on the description field.
