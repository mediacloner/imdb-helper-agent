import fs from 'fs';
import path from 'path';
import neo4j from 'neo4j-driver';

const GRAPH_JSON_PATH = process.env.GRAPH_JSON_PATH ?? '../crawler/output/graph.json';
const NEO4J_URI = process.env.NEO4J_URI ?? 'bolt://localhost:7687';
const NEO4J_USER = process.env.NEO4J_USER ?? 'neo4j';
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD ?? 'password';
const BATCH_SIZE = 100;

const resolvedPath = path.resolve(GRAPH_JSON_PATH);

if (!fs.existsSync(resolvedPath)) {
  console.error(`Graph JSON file not found: ${resolvedPath}`);
  process.exit(1);
}

const graphData = JSON.parse(fs.readFileSync(resolvedPath, 'utf-8'));
const nodes = graphData.nodes ?? [];
const edges = graphData.edges ?? [];

const driver = neo4j.driver(
  NEO4J_URI,
  neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD)
);

function chunk(array, size) {
  const chunks = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

async function importNodes(session) {
  const batches = chunk(nodes, BATCH_SIZE);
  let totalImported = 0;

  for (const batch of batches) {
    const params = batch.map((node) => ({
      node_id: node.node_id,
      type: node.type ?? null,
      url: node.url ?? null,
      description: node.description ?? null,
      capabilities: JSON.stringify(node.capabilities ?? null),
      available_elements: JSON.stringify(node.available_elements ?? null),
    }));

    await session.run(
      `
      UNWIND $params AS p
      MERGE (s:UIState { node_id: p.node_id })
      SET
        s.type = p.type,
        s.url = p.url,
        s.description = p.description,
        s.capabilities = p.capabilities,
        s.available_elements = p.available_elements
      `,
      { params }
    );

    totalImported += batch.length;
    console.log(`  Nodes: imported ${totalImported} / ${nodes.length}`);
  }

  return totalImported;
}

async function importEdges(session) {
  const batches = chunk(edges, BATCH_SIZE);
  let totalImported = 0;

  for (const batch of batches) {
    const params = batch.map((edge) => ({
      source_id: edge.source_node,
      target_id: edge.target_node,
      edge_id: edge.edge_id,
      interaction_type: edge.interaction_type ?? null,
      target_element_id: edge.target_element_id ?? null,
    }));

    await session.run(
      `
      UNWIND $params AS p
      MATCH (source:UIState { node_id: p.source_id })
      MATCH (target:UIState { node_id: p.target_id })
      MERGE (source)-[r:NAVIGATES_TO { edge_id: p.edge_id }]->(target)
      SET
        r.interaction_type = p.interaction_type,
        r.target_element_id = p.target_element_id
      `,
      { params }
    );

    totalImported += batch.length;
    console.log(`  Edges: imported ${totalImported} / ${edges.length}`);
  }

  return totalImported;
}

const session = driver.session();

try {
  console.log(`Reading graph data from: ${resolvedPath}`);
  console.log(`  Nodes to import: ${nodes.length}`);
  console.log(`  Edges to import: ${edges.length}`);
  console.log(`  Batch size: ${BATCH_SIZE}\n`);

  console.log('Clearing existing graph data...');
  await session.run('MATCH (n:UIState) DETACH DELETE n');
  console.log('  Done.\n');

  console.log('Importing nodes...');
  const nodeCount = await importNodes(session);

  console.log('\nImporting edges...');
  const edgeCount = await importEdges(session);

  console.log(`\nImport complete. Nodes: ${nodeCount}, Edges: ${edgeCount}`);
} catch (err) {
  console.error('Import failed:', err.message);
  process.exit(1);
} finally {
  await session.close();
  await driver.close();
}
