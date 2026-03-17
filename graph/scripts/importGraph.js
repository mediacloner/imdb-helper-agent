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

// Critical nodes that must always exist in the graph regardless of crawler output.
// Each entry has: node_id, url, description, and optional parentUrl (the node that
// links TO this one). Nodes are created with MERGE so existing crawler data is preserved.
const CRITICAL_NODES = [
  // ── Inception sub-pages ────────────────────────────────────────────────────
  { node_id: 'critical_tt1375666_reviews',        url: 'https://www.imdb.com/title/tt1375666/reviews',         description: 'Inception (2010) - User Reviews - IMDb',                         parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'User Reviews' },
  { node_id: 'critical_tt1375666_trivia',         url: 'https://www.imdb.com/title/tt1375666/trivia',          description: 'Inception (2010) - Trivia - Did You Know - IMDb',                 parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Trivia' },
  { node_id: 'critical_tt1375666_goofs',          url: 'https://www.imdb.com/title/tt1375666/goofs',           description: 'Inception (2010) - Goofs - Movie Mistakes - IMDb',                parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Goofs' },
  { node_id: 'critical_tt1375666_quotes',         url: 'https://www.imdb.com/title/tt1375666/quotes',          description: 'Inception (2010) - Quotes - Famous Lines - IMDb',                 parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Quotes' },
  { node_id: 'critical_tt1375666_awards',         url: 'https://www.imdb.com/title/tt1375666/awards',          description: 'Inception (2010) - Awards - Oscar Nominations - IMDb',            parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Awards' },
  { node_id: 'critical_tt1375666_fullcredits',    url: 'https://www.imdb.com/title/tt1375666/fullcredits',     description: 'Inception (2010) - Full Cast & Crew - Full Credits - IMDb',       parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Full Cast & Crew' },
  { node_id: 'critical_tt1375666_parentalguide',  url: 'https://www.imdb.com/title/tt1375666/parentalguide',  description: 'Inception (2010) - Parental Guide - Age Rating Content - IMDb',   parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Parents Guide' },
  { node_id: 'critical_tt1375666_technical',      url: 'https://www.imdb.com/title/tt1375666/technical',      description: 'Inception (2010) - Technical Specs - Runtime - IMDb',             parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Technical Specs' },
  { node_id: 'critical_tt1375666_releaseinfo',    url: 'https://www.imdb.com/title/tt1375666/releaseinfo',    description: 'Inception (2010) - Release Dates - Alternate Titles - AKA - IMDb', parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Release Dates' },
  { node_id: 'critical_tt1375666_soundtrack',     url: 'https://www.imdb.com/title/tt1375666/soundtrack',     description: 'Inception (2010) - Soundtrack - Music - IMDb',                    parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Soundtrack' },
  { node_id: 'critical_tt1375666_plotsummary',    url: 'https://www.imdb.com/title/tt1375666/plotsummary',    description: 'Inception (2010) - Plot Summary - Synopsis - IMDb',               parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Plot Summary' },
  { node_id: 'critical_tt1375666_companycredits', url: 'https://www.imdb.com/title/tt1375666/companycredits', description: 'Inception (2010) - Company Credits - Production Companies - IMDb', parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Company Credits' },
  { node_id: 'critical_tt1375666_locations',      url: 'https://www.imdb.com/title/tt1375666/locations',      description: 'Inception (2010) - Filming Locations - Filming & Production - IMDb', parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Filming Locations' },
  { node_id: 'critical_tt1375666_keywords',       url: 'https://www.imdb.com/title/tt1375666/keywords',       description: 'Inception (2010) - Keywords - IMDb',                              parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Keywords' },
  { node_id: 'critical_tt1375666_externalsites',  url: 'https://www.imdb.com/title/tt1375666/externalsites',  description: 'Inception (2010) - External Sites - Official Website - Social Media - IMDb', parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'External Sites' },
  { node_id: 'critical_tt1375666_videogallery',   url: 'https://www.imdb.com/title/tt1375666/videogallery',   description: 'Inception (2010) - Video Gallery - Trailers - Clips - IMDb',      parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Videos & Trailers' },
  { node_id: 'critical_tt1375666_mediaindex',     url: 'https://www.imdb.com/title/tt1375666/mediaindex',     description: 'Inception (2010) - Photo Gallery - Still Photos - IMDb',          parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Photos' },
  { node_id: 'critical_tt1375666_movieconnections', url: 'https://www.imdb.com/title/tt1375666/movieconnections', description: 'Inception (2010) - Movie Connections - Referenced In - Spoofs - IMDb', parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'Movie Connections' },
  { node_id: 'critical_tt1375666_faq',            url: 'https://www.imdb.com/title/tt1375666/faq',            description: 'Inception (2010) - FAQ - Frequently Asked Questions - IMDb',     parentUrl: 'https://www.imdb.com/title/tt1375666/', edgeLabel: 'FAQ' },
  // ── Home → chart pages ────────────────────────────────────────────────────
  { node_id: 'critical_chart_top250',      url: 'https://www.imdb.com/chart/top/',           description: 'IMDb Top 250 Movies - Best Rated Films - IMDb',              parentUrl: 'https://www.imdb.com/', edgeLabel: 'Top 250 Movies' },
  { node_id: 'critical_chart_bottom100',   url: 'https://www.imdb.com/chart/bottom/',         description: 'IMDb Bottom 100 - Lowest Rated Movies - Worst Films - IMDb', parentUrl: 'https://www.imdb.com/', edgeLabel: 'Bottom 100 Movies' },
  { node_id: 'critical_chart_boxoffice',   url: 'https://www.imdb.com/chart/boxoffice/',      description: 'IMDb Top Box Office - Movies Playing Now in Theaters - IMDb', parentUrl: 'https://www.imdb.com/', edgeLabel: 'Box Office' },
  { node_id: 'critical_chart_moviemeter',  url: 'https://www.imdb.com/chart/moviemeter/',     description: 'IMDb Most Popular Movies - MovieMeter - IMDb',               parentUrl: 'https://www.imdb.com/', edgeLabel: 'Most Popular Movies' },
  { node_id: 'critical_chart_toptv',       url: 'https://www.imdb.com/chart/toptv/',          description: 'IMDb Top 250 TV Shows - Best Rated TV Series - IMDb',        parentUrl: 'https://www.imdb.com/', edgeLabel: 'Top 250 TV Shows' },
  { node_id: 'critical_chart_starmeter',   url: 'https://www.imdb.com/chart/starmeter/',      description: 'IMDb STARmeter - Most Popular Celebrities - Celebrity Rankings - IMDb', parentUrl: 'https://www.imdb.com/', edgeLabel: 'STARmeter' },
  { node_id: 'critical_chart_videogame',   url: 'https://www.imdb.com/chart/videogamemeter/', description: 'IMDb Most Popular Video Games - Video Game Chart - IMDb',    parentUrl: 'https://www.imdb.com/', edgeLabel: 'Video Game Chart' },
  // ── Home → feature pages ──────────────────────────────────────────────────
  { node_id: 'critical_calendar',          url: 'https://www.imdb.com/calendar',              description: 'IMDb Release Calendar - Upcoming Releases - IMDb',           parentUrl: 'https://www.imdb.com/', edgeLabel: 'Release Calendar' },
  { node_id: 'critical_awards_central',    url: 'https://www.imdb.com/awards-central/',       description: 'IMDb Awards Central - Emmy Oscar Golden Globe Cannes - IMDb', parentUrl: 'https://www.imdb.com/', edgeLabel: 'Awards Central' },
  { node_id: 'critical_born_today',        url: 'https://www.imdb.com/born-today/',            description: 'IMDb Born Today - Celebrities with Birthdays Today - IMDb',  parentUrl: 'https://www.imdb.com/', edgeLabel: 'Born Today' },
  { node_id: 'critical_news_movie',        url: 'https://www.imdb.com/news/movie/',            description: 'IMDb Movie News - Editorial Picks - Featured Articles - IMDb', parentUrl: 'https://www.imdb.com/', edgeLabel: 'Movie News' },
  { node_id: 'critical_search_title',      url: 'https://www.imdb.com/search/title/',          description: 'IMDb Advanced Title Search - Filter Movies - IMDb',          parentUrl: 'https://www.imdb.com/', edgeLabel: 'Advanced Search' },
  { node_id: 'critical_find',              url: 'https://www.imdb.com/find/',                  description: 'IMDb Search - Find Movies TV Shows People - IMDb',           parentUrl: 'https://www.imdb.com/', edgeLabel: null },
  // ── Awards sub-pages (from Awards Central) ────────────────────────────────
  { node_id: 'critical_oscars',            url: 'https://www.imdb.com/oscars/',                description: 'Academy Awards - Oscar Best Picture Winners - Oscar Nominees - IMDb', parentUrl: 'https://www.imdb.com/awards-central/', edgeLabel: 'Oscars' },
  { node_id: 'critical_emmys',             url: 'https://www.imdb.com/emmys/',                 description: 'Emmy Awards - Television Emmy Award Winners - Prime Time - IMDb',    parentUrl: 'https://www.imdb.com/awards-central/', edgeLabel: 'Emmy Awards' },
  { node_id: 'critical_golden_globes',     url: 'https://www.imdb.com/event/ev0000292/overview/', description: 'Golden Globe Awards - Winners and Nominees - IMDb',            parentUrl: 'https://www.imdb.com/awards-central/', edgeLabel: 'Golden Globes' },
  { node_id: 'critical_cannes',            url: 'https://www.imdb.com/event/ev0000147/overview/', description: 'Cannes Film Festival - Palme d\'Or Winners - Festival Awards - IMDb', parentUrl: 'https://www.imdb.com/awards-central/', edgeLabel: 'Cannes Film Festival' },
  { node_id: 'critical_bafta',             url: 'https://www.imdb.com/event/ev0000123/overview/', description: 'BAFTA Film Awards - Winners and Nominees - IMDb',                parentUrl: 'https://www.imdb.com/awards-central/', edgeLabel: 'BAFTA Awards' },
  // ── Person pages (from search/find) ──────────────────────────────────────
  { node_id: 'critical_person_nolan',      url: 'https://www.imdb.com/name/nm0634240/',        description: 'Christopher Nolan - Filmmaker Filmography - Biography - IMDb', parentUrl: 'https://www.imdb.com/find/', edgeLabel: 'Christopher Nolan' },
  { node_id: 'critical_person_hanks',      url: 'https://www.imdb.com/name/nm0000158/',        description: 'Tom Hanks - Actor Filmography - Biography - STARmeter - IMDb',  parentUrl: 'https://www.imdb.com/find/', edgeLabel: 'Tom Hanks' },
  { node_id: 'critical_person_scorsese',   url: 'https://www.imdb.com/name/nm0000217/',        description: 'Martin Scorsese - Director Filmography - Biography - IMDb',     parentUrl: 'https://www.imdb.com/find/', edgeLabel: 'Martin Scorsese' },
  // ── TV show episode guide pages ────────────────────────────────────────────
  { node_id: 'critical_bb_episodes',       url: 'https://www.imdb.com/title/tt0903747/episodes/', description: 'Breaking Bad - Episode Guide - Season Episodes - IMDb',         parentUrl: 'https://www.imdb.com/title/tt0903747/', edgeLabel: 'Episode Guide' },
  { node_id: 'critical_got_episodes',      url: 'https://www.imdb.com/title/tt0944947/episodes/', description: 'Game of Thrones - Episode Guide - Season Episodes - IMDb',       parentUrl: 'https://www.imdb.com/title/tt0944947/', edgeLabel: 'Episode Guide' },
  { node_id: 'critical_frasier_episodes',  url: 'https://www.imdb.com/title/tt0106004/episodes/', description: 'Frasier - Episode Guide - Season Episodes - IMDb',              parentUrl: 'https://www.imdb.com/title/tt0106004/', edgeLabel: 'Episode Guide' },
  { node_id: 'critical_sopranos_episodes', url: 'https://www.imdb.com/title/tt0141842/episodes/', description: 'The Sopranos - Episode Guide - Season Episodes - Ratings - IMDb', parentUrl: 'https://www.imdb.com/title/tt0141842/', edgeLabel: 'Episode Guide' },
  { node_id: 'critical_office_episodes',   url: 'https://www.imdb.com/title/tt0386676/episodes/', description: 'The Office - Episode Guide - Season Episodes - IMDb',            parentUrl: 'https://www.imdb.com/title/tt0386676/', edgeLabel: 'Episode Guide' },
  // ── Contribution portal ────────────────────────────────────────────────────
  { node_id: 'critical_contribute',        url: 'https://contribute.imdb.com/',               description: 'IMDb Contribution Portal - Report Error - Add Title - Edit Data', parentUrl: 'https://www.imdb.com/', edgeLabel: 'Add/Edit IMDb Data' },
];

async function injectCriticalNodesAndEdges(session) {
  console.log('\nInjecting critical nodes and edges…');
  let nodesCreated = 0;
  let edgesCreated = 0;

  for (const node of CRITICAL_NODES) {
    // MERGE the target node — creates it if missing, leaves existing data untouched
    await session.run(
      `MERGE (n:UIState {url: $url})
       ON CREATE SET
         n.node_id      = $node_id,
         n.description  = $description,
         n.type         = 'injected',
         n.capabilities = '{}',
         n.available_elements = '[]'
       RETURN n`,
      { url: node.url, node_id: node.node_id, description: node.description },
    );
    nodesCreated++;

    if (!node.parentUrl) continue;

    // MERGE the edge from parent → this node (match parent by URL with/without slash)
    const result = await session.run(
      `MATCH (src:UIState)
         WHERE src.url = $src OR src.url = $src + '/' OR src.url = $src_slash OR src.url = $src_slash + '/'
       MATCH (tgt:UIState)
         WHERE tgt.url = $tgt OR tgt.url = $tgt + '/' OR tgt.url = $tgt_slash OR tgt.url = $tgt_slash + '/'
       MERGE (src)-[r:NAVIGATES_TO {edge_id: $edge_id}]->(tgt)
       ON CREATE SET r.interaction_type = 'click', r.target_element_id = $label
       RETURN count(r) AS cnt`,
      {
        src:       node.parentUrl.replace(/\/$/, ''),
        src_slash: node.parentUrl.replace(/\/$/, '') + '/',
        tgt:       node.url.replace(/\/$/, ''),
        tgt_slash: node.url.replace(/\/$/, '') + '/',
        edge_id:   `critical_${Buffer.from(node.parentUrl + '→' + node.url).toString('base64').slice(0, 24)}`,
        label:     node.edgeLabel ?? null,
      },
    );
    edgesCreated += result.records[0]?.get('cnt').toNumber() ?? 0;
  }

  console.log(`  Critical nodes: ${nodesCreated} processed, edges: ${edgesCreated} created`);
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

  await injectCriticalNodesAndEdges(session);

  console.log(`\nImport complete. Nodes: ${nodeCount}, Edges: ${edgeCount}`);
} catch (err) {
  console.error('Import failed:', err.message);
  process.exit(1);
} finally {
  await session.close();
  await driver.close();
}
