/**
 * Cypher query helpers for use by the RAG service.
 * Each function accepts a neo4j-driver Session instance and returns the raw query result.
 */

/**
 * Find a UIState node by its URL.
 * @param {import('neo4j-driver').Session} session
 * @param {string} url
 * @returns {Promise<import('neo4j-driver').QueryResult>}
 */
export async function findStateByUrl(session, url) {
  return session.run(
    `
    MATCH (s:UIState { url: $url })
    RETURN s
    `,
    { url }
  );
}

/**
 * Find the shortest path between two UIState nodes using their node_id values.
 * @param {import('neo4j-driver').Session} session
 * @param {string} startNodeId
 * @param {string} endNodeId
 * @returns {Promise<import('neo4j-driver').QueryResult>}
 */
export async function findPathBetweenStates(session, startNodeId, endNodeId) {
  return session.run(
    `
    MATCH (start:UIState { node_id: $startNodeId }), (end:UIState { node_id: $endNodeId })
    MATCH p = shortestPath((start)-[:NAVIGATES_TO*]->(end))
    RETURN p
    `,
    { startNodeId, endNodeId }
  );
}

/**
 * Return the capabilities and available elements of a UIState node.
 * @param {import('neo4j-driver').Session} session
 * @param {string} nodeId
 * @returns {Promise<import('neo4j-driver').QueryResult>}
 */
export async function getStateCapabilities(session, nodeId) {
  return session.run(
    `
    MATCH (s:UIState { node_id: $nodeId })
    RETURN s.node_id AS node_id, s.capabilities AS capabilities, s.available_elements AS available_elements
    `,
    { nodeId }
  );
}

/**
 * Search UIState nodes whose description contains the given keyword (case-insensitive).
 * @param {import('neo4j-driver').Session} session
 * @param {string} keyword
 * @returns {Promise<import('neo4j-driver').QueryResult>}
 */
export async function searchStatesByDescription(session, keyword) {
  return session.run(
    `
    MATCH (s:UIState)
    WHERE toLower(s.description) CONTAINS toLower($keyword)
    RETURN s
    ORDER BY s.node_id
    `,
    { keyword }
  );
}
