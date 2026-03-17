import os
import re
from typing import Any

from neo4j import GraphDatabase, Driver

# Known-good start nodes to anchor fallback path searches.
# IMPORTANT: Only include generic IMDb entry points — NOT specific movie/title pages.
# Including a specific title (e.g. Inception) causes the graph to return
# title-centric paths (Inception→reviews, Inception→awards, etc.) for
# completely unrelated queries, producing Inception false-positives across
# many question categories.
_GOOD_START_URLS = [
    "https://www.imdb.com/",
    "https://www.imdb.com",
    "https://www.imdb.com/search/title/",
    "https://www.imdb.com/awards-central/",
    "https://www.imdb.com/chart/top/",
    "https://www.imdb.com/chart/moviemeter/",
    "https://www.imdb.com/news/movie/",
    "https://www.imdb.com/chart/starmeter/",
]

# Words that carry no meaningful semantic weight when matching graph node descriptions
_MATCH_STOP_WORDS = {
    "how", "what", "when", "where", "which", "does", "have", "will", "can",
    "find", "look", "show", "view", "open", "goto", "page", "imdb", "website",
    "movie", "film", "watch", "want", "this", "that", "with", "from", "into",
    "some", "more", "also", "then", "list", "title", "about", "using", "only",
    "specific", "another", "other", "same", "just", "make", "would", "should",
    "each", "their", "here", "there", "your", "getting", "looking", "finding",
}


def _significant_words(text: str) -> list[str]:
    """Extract meaningful lowercase words from a description for fuzzy matching."""
    return [w for w in re.findall(r'[a-z]+', text.lower())
            if len(w) > 3 and w not in _MATCH_STOP_WORDS]


class GraphClient:
    def __init__(self) -> None:
        uri: str = os.environ["NEO4J_URI"]
        user: str = os.environ["NEO4J_USER"]
        password: str = os.environ["NEO4J_PASSWORD"]
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def find_path(self, start_description: str, end_description: str) -> list[dict[str, Any]]:
        """Find a path between two UIState nodes matching the given descriptions.

        Returns a list of step dicts, each containing node_id, url, description,
        and action (edge interaction_type + target_element_id).

        Strategy (in order of preference):
        1. Exact substring match on up to 5 end candidates, shortest path wins.
        2. Good-start-node fallback with exact substring match.
        3. Word-level fuzzy match: extract significant words from end_description,
           score nodes by how many words match, use top candidates with good starts.
        4. Single-word fallback: try the most distinctive word alone.
        5. Search-page fallback.
        """
        records = self._try_exact_match(start_description, end_description)

        if not records:
            records = self._try_good_start_exact(end_description)

        if not records:
            end_words = _significant_words(end_description)
            if end_words:
                records = self._try_word_fuzzy(end_words)

        if not records:
            # Last-resort: try each significant word individually as a substring
            for word in _significant_words(end_description):
                records = self._try_good_start_exact(word)
                if records:
                    break
        steps: list[dict[str, Any]] = self._records_to_steps(records)

        # Fallback: if nothing found, return the search page so the user
        # can at least see how to search on IMDb
        if not steps:
            steps = self._search_fallback()

        return steps

    def _records_to_steps(self, records: list) -> list[dict[str, Any]]:
        return [
            {
                "node_id": r["node_id"],
                "url": r["url"],
                "description": r["description"],
                "action": {
                    "interaction_type": r["interaction_type"],
                    "target_element_id": r["target_element_id"],
                },
            }
            for r in records
        ]

    def _try_exact_match(self, start_description: str, end_description: str) -> list:
        """Primary query: exact substring match on up to 5 end candidates."""
        query = """
        MATCH (end:UIState)
        WHERE toLower(end.description) CONTAINS toLower($end_desc)
           OR toLower(end.node_id)    CONTAINS toLower($end_desc)
        WITH end LIMIT 5
        MATCH (start:UIState)
        WHERE (toLower(start.description) CONTAINS toLower($start_desc)
           OR toLower(start.node_id)    CONTAINS toLower($start_desc))
          AND start <> end
        WITH end, start LIMIT 10
        MATCH path = shortestPath((start)-[:NAVIGATES_TO*1..20]->(end))
        WITH nodes(path) AS path_nodes, relationships(path) AS path_rels, length(path) AS len
        ORDER BY len ASC LIMIT 1
        UNWIND range(0, size(path_nodes) - 1) AS idx
        WITH path_nodes[idx] AS n,
             CASE WHEN idx < size(path_rels) THEN path_rels[idx] ELSE null END AS r
        RETURN
            n.node_id             AS node_id,
            n.url                 AS url,
            n.description         AS description,
            r.interaction_type    AS interaction_type,
            r.target_element_id   AS target_element_id
        LIMIT 30
        """
        records, _, _ = self._driver.execute_query(
            query, start_desc=start_description, end_desc=end_description,
        )
        return records

    def _try_good_start_exact(self, end_description: str) -> list:
        """Fallback: shortest path from any known-good start node, exact substring match."""
        query = """
        MATCH (end:UIState)
        WHERE toLower(end.description) CONTAINS toLower($end_desc)
           OR toLower(end.node_id)    CONTAINS toLower($end_desc)
        WITH collect(end) AS ends
        UNWIND ends AS end
        MATCH (start:UIState)
        WHERE start.url IN $good_starts AND start <> end
        MATCH path = shortestPath((start)-[:NAVIGATES_TO*1..15]->(end))
        WITH nodes(path) AS path_nodes, relationships(path) AS path_rels, length(path) AS len
        ORDER BY len ASC LIMIT 1
        UNWIND range(0, size(path_nodes) - 1) AS idx
        WITH path_nodes[idx] AS n,
             CASE WHEN idx < size(path_rels) THEN path_rels[idx] ELSE null END AS r
        RETURN
            n.node_id             AS node_id,
            n.url                 AS url,
            n.description         AS description,
            r.interaction_type    AS interaction_type,
            r.target_element_id   AS target_element_id
        LIMIT 30
        """
        records, _, _ = self._driver.execute_query(
            query, end_desc=end_description, good_starts=_GOOD_START_URLS,
        )
        return records

    def _try_word_fuzzy(self, end_words: list[str]) -> list:
        """Fuzzy fallback: score nodes by how many significant words from end_description match."""
        query = """
        MATCH (end:UIState)
        WHERE ANY(word IN $end_words WHERE
              toLower(end.description) CONTAINS word
           OR toLower(end.node_id)    CONTAINS word)
        WITH end,
             size([w IN $end_words WHERE
                   toLower(end.description) CONTAINS w
                OR toLower(end.node_id)    CONTAINS w]) AS score
        ORDER BY score DESC LIMIT 10
        MATCH (start:UIState)
        WHERE start.url IN $good_starts AND start <> end
        MATCH path = shortestPath((start)-[:NAVIGATES_TO*1..15]->(end))
        WITH nodes(path) AS path_nodes, relationships(path) AS path_rels,
             length(path) AS len, end, score
        ORDER BY score DESC, len ASC LIMIT 1
        UNWIND range(0, size(path_nodes) - 1) AS idx
        WITH path_nodes[idx] AS n,
             CASE WHEN idx < size(path_rels) THEN path_rels[idx] ELSE null END AS r
        RETURN
            n.node_id             AS node_id,
            n.url                 AS url,
            n.description         AS description,
            r.interaction_type    AS interaction_type,
            r.target_element_id   AS target_element_id
        LIMIT 30
        """
        records, _, _ = self._driver.execute_query(
            query, end_words=end_words, good_starts=_GOOD_START_URLS,
        )
        return records

    def _search_fallback(self) -> list[dict[str, Any]]:
        """Return the IMDb search/find state as a single-step fallback path."""
        query = """
        MATCH (n:UIState)
        WHERE toLower(n.node_id) CONTAINS 'find'
           OR toLower(n.description) CONTAINS 'search'
           OR toLower(n.description) CONTAINS 'find'
        RETURN n.node_id AS node_id, n.url AS url, n.description AS description
        LIMIT 1
        """
        records, _, _ = self._driver.execute_query(query)
        if not records:
            return []
        r = records[0]
        return [{
            "node_id": r["node_id"],
            "url": r["url"],
            "description": r["description"],
            "action": {"interaction_type": None, "target_element_id": None},
        }]

    def get_state(self, node_id: str) -> dict[str, Any]:
        """Return a single UIState node's data by node_id."""
        query = """
        MATCH (n:UIState {node_id: $node_id})
        RETURN
            n.node_id        AS node_id,
            n.url            AS url,
            n.description    AS description,
            n.capabilities   AS capabilities,
            n.available_elements AS available_elements
        LIMIT 1
        """
        records, _, _ = self._driver.execute_query(query, node_id=node_id)
        if not records:
            return {}
        record = records[0]
        return {
            "node_id": record["node_id"],
            "url": record["url"],
            "description": record["description"],
            "capabilities": record["capabilities"],
            "available_elements": record["available_elements"],
        }

    def search_states(self, keyword: str) -> list[dict[str, Any]]:
        """Search UIState nodes where description contains the given keyword."""
        query = """
        MATCH (n:UIState)
        WHERE n.description CONTAINS $keyword
        RETURN
            n.node_id        AS node_id,
            n.url            AS url,
            n.description    AS description
        LIMIT 20
        """
        records, _, _ = self._driver.execute_query(query, keyword=keyword)
        return [
            {
                "node_id": record["node_id"],
                "url": record["url"],
                "description": record["description"],
            }
            for record in records
        ]

    def close(self) -> None:
        """Close the Neo4j driver."""
        self._driver.close()
