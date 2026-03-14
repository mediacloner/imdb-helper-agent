/**
 * index.js
 * Entry point for the IMDB Semantic Crawler.
 * Reads configuration from environment variables, runs the crawl,
 * and writes the resulting knowledge graph to a JSON file.
 */

import fs from 'fs';
import path from 'path';
import { crawl } from './crawler.js';

const START_URL = process.env.START_URL || 'https://www.imdb.com';
const MAX_PAGES = parseInt(process.env.MAX_PAGES || '10', 10);
const OUTPUT_PATH = '/app/output/graph.json';

async function main() {
  console.log('[index] IMDB Semantic Crawler — Phase 1');
  console.log(`[index] Start URL : ${START_URL}`);
  console.log(`[index] Max pages : ${MAX_PAGES}`);
  console.log(`[index] Output    : ${OUTPUT_PATH}`);
  console.log('');

  let graph;
  try {
    graph = await crawl(START_URL, MAX_PAGES);
  } catch (err) {
    console.error('[index] Crawl failed:', err);
    process.exit(1);
  }

  // Ensure the output directory exists
  const outputDir = path.dirname(OUTPUT_PATH);
  try {
    fs.mkdirSync(outputDir, { recursive: true });
  } catch (mkdirErr) {
    console.error(`[index] Could not create output directory "${outputDir}":`, mkdirErr);
    process.exit(1);
  }

  // Write the graph to disk
  try {
    fs.writeFileSync(OUTPUT_PATH, JSON.stringify(graph, null, 2), 'utf-8');
    console.log(`\n[index] Graph written to ${OUTPUT_PATH}`);
    console.log(`[index] Summary — nodes: ${graph.nodes.length}, edges: ${graph.edges.length}`);
  } catch (writeErr) {
    console.error(`[index] Failed to write output file:`, writeErr);
    process.exit(1);
  }
}

main();
