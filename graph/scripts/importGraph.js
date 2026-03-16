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

// Critical edges that must always exist regardless of what the crawler produced.
// These connect key navigation landmarks (homepage → charts, Inception → sub-pages)
// and are idempotently re-injected after every import using MERGE.
const CRITICAL_EDGES = [
  // ── Home → utility pages ─────────────────────────────────────────────────
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/chart/top/',              type: 'click',        label: 'Top 250 Movies' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/chart/bottom/',           type: 'click',        label: 'Bottom 100 Movies' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/chart/boxoffice/',        type: 'click',        label: 'Box Office' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/chart/moviemeter/',       type: 'click',        label: 'Most Popular Movies' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/chart/toptv/',            type: 'click',        label: 'Top 250 TV Shows' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/chart/starmeter/',        type: 'click',        label: 'STARmeter' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/calendar',                type: 'click',        label: 'Release Calendar' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/awards-central/',         type: 'click',        label: 'Awards Central' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/oscars/',                 type: 'click',        label: 'Oscars' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/news/movie/',             type: 'click',        label: 'Movie News' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/search/title/',           type: 'click',        label: 'Advanced Search' },
  { src: 'https://www.imdb.com',                    tgt: 'https://www.imdb.com/find/',                   type: 'search_query', label: null },
  // ── Inception → sub-pages ─────────────────────────────────────────────────
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/reviews',        type: 'click', label: 'User Reviews' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/trivia',         type: 'click', label: 'Trivia' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/goofs',          type: 'click', label: 'Goofs' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/quotes',         type: 'click', label: 'Quotes' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/awards',         type: 'click', label: 'Awards' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/fullcredits',    type: 'click', label: 'Full Cast & Crew' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/parentalguide', type: 'click', label: 'Parents Guide' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/technical',     type: 'click', label: 'Technical Specs' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/releaseinfo',   type: 'click', label: 'Release Dates' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/soundtrack',    type: 'click', label: 'Soundtrack' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/plotsummary',   type: 'click', label: 'Plot Summary' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/companycredits',type: 'click', label: 'Company Credits' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/locations',     type: 'click', label: 'Filming Locations' },
  { src: 'https://www.imdb.com/title/tt1375666/',   tgt: 'https://www.imdb.com/title/tt1375666/keywords',      type: 'click', label: 'Keywords' },
];

async function injectCriticalEdges(session) {
  console.log('\nInjecting critical edges…');
  let injected = 0;

  for (const edge of CRITICAL_EDGES) {
    // Match nodes by URL with or without trailing slash
    const result = await session.run(
      `
      MATCH (src:UIState)
        WHERE src.url = $src OR src.url = $src + '/' OR src.url = $src_slash OR src.url = $src_slash + '/'
      MATCH (tgt:UIState)
        WHERE tgt.url = $tgt OR tgt.url = $tgt + '/' OR tgt.url = $tgt_slash OR tgt.url = $tgt_slash + '/'
      MERGE (src)-[r:NAVIGATES_TO { edge_id: $edge_id }]->(tgt)
      ON CREATE SET r.interaction_type = $itype, r.target_element_id = $label
      RETURN count(r) AS cnt
      `,
      {
        src:       edge.src.replace(/\/$/, ''),
        src_slash: edge.src.replace(/\/$/, '') + '/',
        tgt:       edge.tgt.replace(/\/$/, ''),
        tgt_slash: edge.tgt.replace(/\/$/, '') + '/',
        edge_id:   `critical_${Buffer.from(edge.src + '→' + edge.tgt).toString('base64').slice(0, 24)}`,
        itype:     edge.type,
        label:     edge.label ?? null,
      }
    );
    injected += result.records[0]?.get('cnt').toNumber() ?? 0;
  }

  console.log(`  Critical edges: ${injected} created / ${CRITICAL_EDGES.length} total`);
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

  await injectCriticalEdges(session);

  console.log(`\nImport complete. Nodes: ${nodeCount}, Edges: ${edgeCount}`);
} catch (err) {
  console.error('Import failed:', err.message);
  process.exit(1);
} finally {
  await session.close();
  await driver.close();
}
