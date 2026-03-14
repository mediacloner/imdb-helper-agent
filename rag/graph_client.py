import os
from typing import Any

from neo4j import GraphDatabase, Driver


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
        """
        # Try shortest path from a matching start node
        query = """
        MATCH (end:UIState)
        WHERE toLower(end.description) CONTAINS toLower($end_desc)
           OR toLower(end.node_id)    CONTAINS toLower($end_desc)
        WITH end LIMIT 1
        MATCH (start:UIState)
        WHERE (toLower(start.description) CONTAINS toLower($start_desc)
           OR toLower(start.node_id)    CONTAINS toLower($start_desc))
          AND start <> end
        MATCH path = shortestPath((start)-[:NAVIGATES_TO*1..20]->(end))
        WITH nodes(path) AS path_nodes, relationships(path) AS path_rels
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
            query,
            start_desc=start_description,
            end_desc=end_description,
        )

        # Fallback: find any shortest path to any matching destination node
        if not records:
            query = """
            MATCH (end:UIState)
            WHERE toLower(end.description) CONTAINS toLower($end_desc)
               OR toLower(end.node_id)    CONTAINS toLower($end_desc)
            WITH collect(end) AS ends
            UNWIND ends AS end
            MATCH (start:UIState)
            WHERE start <> end
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
            records, _, _ = self._driver.execute_query(query, end_desc=end_description)
        steps: list[dict[str, Any]] = []
        for record in records:
            step: dict[str, Any] = {
                "node_id": record["node_id"],
                "url": record["url"],
                "description": record["description"],
                "action": {
                    "interaction_type": record["interaction_type"],
                    "target_element_id": record["target_element_id"],
                },
            }
            steps.append(step)

        # Fallback: if nothing found, return the search page so the user
        # can at least see how to search on IMDb
        if not steps:
            steps = self._search_fallback()

        return steps

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
