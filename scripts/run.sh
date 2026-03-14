#!/bin/bash

echo "================================================="
echo " Autonomous Web UI Agent - Docker Runner"
echo "================================================="
echo " 1) Crawl - Small   (10 pages,  ~2 min)"
echo " 2) Crawl - Medium  (30 pages,  ~6 min)"
echo " 3) Crawl - Large   (60 pages, ~12 min)"
echo " 4) Save graph to database (Neo4j import)"
echo " 5) Production stack (Neo4j + RAG + Interface)"
echo "================================================="
echo -n "Enter choice [1-5]: "
read choice

run_crawler() {
    local max_pages=$1
    echo "Starting crawler with MAX_PAGES=${max_pages}..."
    MAX_PAGES=$max_pages docker compose --profile scrape up --build
    echo ""
    echo "Crawl complete. Output: crawler/output/graph.json"
    echo "Run option 4 to import the graph into Neo4j."
}

if [ "$choice" == "1" ]; then
    run_crawler 10

elif [ "$choice" == "2" ]; then
    run_crawler 30

elif [ "$choice" == "3" ]; then
    run_crawler 60

elif [ "$choice" == "4" ]; then
    echo "Importing graph into Neo4j..."
    echo "Making sure Neo4j is running..."
    docker compose --profile production up -d neo4j
    echo "Waiting for Neo4j to be ready..."
    until docker compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1;" > /dev/null 2>&1; do
        echo "  Neo4j not ready yet, retrying in 3s..."
        sleep 3
    done
    echo "Neo4j is ready."
    echo "Running schema init..."
    cd graph && npm install --silent && npm run init-schema
    echo "Importing graph.json..."
    npm run import
    cd ..
    echo ""
    echo "Import complete."
    echo "Neo4j browser: http://localhost:7474"

elif [ "$choice" == "5" ]; then
    echo "Starting Production Profile..."
    docker compose --profile production up --build -d
    echo "Production services are spinning up in the background."
    echo "Pulling local models into Ollama (this may take a few minutes on first run)..."
    docker compose exec ollama ollama pull qwen3:8b
    docker compose exec ollama ollama pull nomic-embed-text
    echo ""
    echo "Neo4j:     http://localhost:7474"
    echo "RAG API:   http://localhost:8000"
    echo "Interface: http://localhost:3000"
    echo "Ollama:    http://localhost:11434"

else
    echo "Invalid choice. Exiting."
    exit 1
fi
