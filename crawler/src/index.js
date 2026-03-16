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
const MAX_PAGES = parseInt(process.env.MAX_PAGES || '200', 10);
const OUTPUT_PATH = '/app/output/graph.json';
const REPORT_PATH = '/app/output/report.md';

function generateReport(graph, startUrl, maxPages, durationMs) {
  const crawledAt = new Date().toISOString();
  const duration = (durationMs / 1000).toFixed(1);

  const lines = [];
  lines.push(`# IMDB Crawler Report`);
  lines.push(`\n**Crawled at:** ${crawledAt}`);
  lines.push(`**Start URL:** ${startUrl}`);
  lines.push(`**Max pages:** ${maxPages}`);
  lines.push(`**Duration:** ${duration}s`);
  lines.push(`**Total nodes:** ${graph.nodes.length}`);
  lines.push(`**Total edges:** ${graph.edges.length}`);

  lines.push(`\n---\n`);
  lines.push(`## Pages Scraped (${graph.nodes.length})\n`);
  for (let i = 0; i < graph.nodes.length; i++) {
    const n = graph.nodes[i];
    lines.push(`${i + 1}. [${n.description}](${n.url})`);
  }

  lines.push(`\n---\n`);
  lines.push(`## Page Details\n`);

  for (const node of graph.nodes) {
    const caps = Object.keys(node.capabilities);
    const elemCount = node.available_elements.length;

    lines.push(`### ${node.node_id}`);
    lines.push(`- **URL:** ${node.url}`);
    lines.push(`- **Title:** ${node.description}`);
    lines.push(`- **Interactive elements:** ${elemCount}`);

    if (caps.length > 0) {
      lines.push(`- **Capabilities:**`);
      for (const cap of caps) {
        const label = cap.replace(/^can_/, '').replace(/_/g, ' ');
        lines.push(`  - ✅ ${label}`);
      }
    } else {
      lines.push(`- **Capabilities:** none detected`);
    }

    const outgoing = graph.edges.filter(e => e.source_node === node.node_id);
    if (outgoing.length > 0) {
      lines.push(`- **Outgoing transitions (${outgoing.length}):**`);
      for (const edge of outgoing.slice(0, 10)) {
        lines.push(`  - \`${edge.interaction_type}\` → \`${edge.target_node}\` via \`${edge.target_element_id}\``);
      }
      if (outgoing.length > 10) {
        lines.push(`  - _...and ${outgoing.length - 10} more_`);
      }
    }

    lines.push('');
  }

  lines.push(`---\n`);
  lines.push(`## Page Type Coverage\n`);
  const types = graph.visitedTypes || [];
  lines.push(`**${types.length} structural types visited:**\n`);
  for (const t of types) {
    lines.push(`- \`${t}\``);
  }

  lines.push(`\n---\n`);
  lines.push(`## Capability Coverage\n`);
  const capCount = {};
  for (const node of graph.nodes) {
    for (const cap of Object.keys(node.capabilities)) {
      capCount[cap] = (capCount[cap] || 0) + 1;
    }
  }
  const sorted = Object.entries(capCount).sort((a, b) => b[1] - a[1]);
  for (const [cap, count] of sorted) {
    const label = cap.replace(/^can_/, '').replace(/_/g, ' ');
    const bar = '█'.repeat(count) + '░'.repeat(graph.nodes.length - count);
    lines.push(`- **${label}:** ${bar} ${count}/${graph.nodes.length} nodes`);
  }

  return lines.join('\n');
}

async function main() {
  console.log('[index] IMDB Semantic Crawler — Phase 1');
  console.log(`[index] Start URL : ${START_URL}`);
  console.log(`[index] Max pages : ${MAX_PAGES}`);
  console.log(`[index] Output    : ${OUTPUT_PATH}`);
  console.log(`[index] Report    : ${REPORT_PATH}`);
  console.log('');

  const startTime = Date.now();

  let graph;
  try {
    graph = await crawl(START_URL, MAX_PAGES);
  } catch (err) {
    console.error('[index] Crawl failed:', err);
    process.exit(1);
  }

  const durationMs = Date.now() - startTime;

  // Ensure the output directory exists
  const outputDir = path.dirname(OUTPUT_PATH);
  try {
    fs.mkdirSync(outputDir, { recursive: true });
  } catch (mkdirErr) {
    console.error(`[index] Could not create output directory "${outputDir}":`, mkdirErr);
    process.exit(1);
  }

  // Write the graph JSON
  try {
    fs.writeFileSync(OUTPUT_PATH, JSON.stringify(graph, null, 2), 'utf-8');
    console.log(`\n[index] Graph written to ${OUTPUT_PATH}`);
    console.log(`[index] Summary — nodes: ${graph.nodes.length}, edges: ${graph.edges.length}`);
  } catch (writeErr) {
    console.error(`[index] Failed to write graph file:`, writeErr);
    process.exit(1);
  }

  // Write the human-readable report
  try {
    const report = generateReport(graph, START_URL, MAX_PAGES, durationMs);
    fs.writeFileSync(REPORT_PATH, report, 'utf-8');
    console.log(`[index] Report written to ${REPORT_PATH}`);
  } catch (writeErr) {
    console.error(`[index] Failed to write report file:`, writeErr);
  }
}

main();
