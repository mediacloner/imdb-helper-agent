# System Architecture Context: Autonomous Web UI Agent

## 1. Project Overview
We are building an Autonomous Web UI Agent designed to map, understand, and interact with web applications (e.g., IMDb, bespoke demo environments, or specialist retail sites). 

Unlike standard text-scraping bots, this system builds a **UI Knowledge Graph**. It maps web pages as 'States' and user interactions as 'Edges'. Once the web application is mapped, the system uses a Retrieval-Augmented Generation (RAG) approach to cross-reference written manuals with its interactive map, ultimately generating visual, step-by-step tutorials (videos or browser extension tooltips) for end-users.

## 2. Core Architecture Phases

### Phase 1: The Semantic Crawler (Playwright)
* **Purpose:** To explore the target website and extract its interactive capabilities.
* **Mechanism:** A headless browser (Playwright) navigates the site. Instead of scraping product text, it parses the DOM for interactive elements (buttons, forms, links) and structural metadata (ARIA roles).
* **Constraints:** Must employ human-like behaviour (throttling speed, handling cookie banners, using transparent User-Agents) to avoid anti-bot detection.

### Phase 2: The UI Knowledge Graph (State & Transition Storage)
* **Purpose:** To store the crawler's findings in a structured, queryable format (e.g., JSON, Neo4j).
* **Nodes (States):** Represent what the user sees (e.g., "Main Catalogue Page", "Filter Modal Open"). Nodes contain a `capabilities` object detailing what can be done in that state.
* **Edges (Actions):** Represent the exact interactions required to move between nodes (e.g., `interaction_type: "click"`, target CSS selector).

### Phase 3: The Knowledge Synthesis (RAG & LLM Brain)
* **Purpose:** To translate natural language user queries into executable UI pathways.
* **Mechanism:** User manuals and documentation are embedded in a vector database. When a user asks a question, the LLM retrieves the manual's instructions, translates the user's intent, and queries the UI Knowledge Graph to find the exact sequence of clicks required to execute the task.

### Phase 4: Output Delivery
The agent delivers its guidance via a **Chat Interface**:
* Users ask questions in a conversational chat interface.
* The agent responds with a mix of text explanations and on-the-fly generated video tutorials (`.webm` or `.mp4` recorded via a backend Playwright script) showing the exact sequence of steps.

## 3. Standardised Data Schema (Graph Example)
The system relies on mapping the environment using the following JSON schema logic:

{
  "nodes": [
    {
      "node_id": "state_page_film_001",
      "type": "page",
      "description": "Main film overview page",
      "capabilities": {
        "can_view_full_cast": true
      },
      "available_elements": [
        {
          "element_id": "link_full_cast",
          "role": "link",
          "css_selector": "a:has-text('Full Cast & Crew')"
        }
      ]
    }
  ],
  "edges": [
    {
      "edge_id": "action_click_cast_001",
      "source_node": "state_page_film_001",
      "target_node": "state_page_cast_list_001",
      "interaction_type": "click",
      "target_element_id": "link_full_cast"
    }
  ]
}