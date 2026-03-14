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
        query = """
        MATCH (start:UIState), (end:UIState)
        WHERE start.description CONTAINS $start_desc
          AND end.description CONTAINS $end_desc
        MATCH path = shortestPath((start)-[:TRANSITION*..20]->(end))
        WITH nodes(path) AS path_nodes, relationships(path) AS path_rels
        UNWIND range(0, size(path_nodes) - 1) AS idx
        WITH path_nodes[idx] AS n,
             CASE WHEN idx < size(path_rels) THEN path_rels[idx] ELSE null END AS r
        RETURN
            n.node_id        AS node_id,
            n.url            AS url,
            n.description    AS description,
            r.interaction_type    AS interaction_type,
            r.target_element_id   AS target_element_id
        """
        records, _, _ = self._driver.execute_query(
            query,
            start_desc=start_description,
            end_desc=end_description,
        )
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
        return steps

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
