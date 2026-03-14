import neo4j from 'neo4j-driver';

const NEO4J_URI = process.env.NEO4J_URI ?? 'bolt://localhost:7687';
const NEO4J_USER = process.env.NEO4J_USER ?? 'neo4j';
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD ?? 'password';

const driver = neo4j.driver(
  NEO4J_URI,
  neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD)
);

const session = driver.session();

const operations = [
  {
    label: 'Uniqueness constraint: UIState.node_id',
    cypher: `
      CREATE CONSTRAINT uistate_node_id_unique IF NOT EXISTS
      FOR (s:UIState) REQUIRE s.node_id IS UNIQUE
    `,
  },
  {
    label: 'Uniqueness constraint: UIAction.edge_id',
    cypher: `
      CREATE CONSTRAINT uiaction_edge_id_unique IF NOT EXISTS
      FOR (a:UIAction) REQUIRE a.edge_id IS UNIQUE
    `,
  },
  {
    label: 'Index: UIState.url',
    cypher: `
      CREATE INDEX uistate_url_index IF NOT EXISTS
      FOR (s:UIState) ON (s.url)
    `,
  },
  {
    label: 'Index: UIState.description',
    cypher: `
      CREATE INDEX uistate_description_index IF NOT EXISTS
      FOR (s:UIState) ON (s.description)
    `,
  },
];

try {
  for (const op of operations) {
    const result = await session.run(op.cypher);
    console.log(`[OK] ${op.label}`);
    console.log(`     Summary: ${JSON.stringify(result.summary.counters._stats)}`);
  }
  console.log('\nSchema initialisation complete.');
} catch (err) {
  console.error('Schema initialisation failed:', err.message);
  process.exit(1);
} finally {
  await session.close();
  await driver.close();
}
