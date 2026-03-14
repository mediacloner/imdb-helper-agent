#!/bin/bash

show_menu() {
    echo "================================================="
    echo " Autonomous Web UI Agent - Docker Runner"
    echo "================================================="
    echo " 1) Crawl - Small   (10 pages,  ~2 min)"
    echo " 2) Crawl - Medium  (30 pages,  ~6 min)"
    echo " 3) Crawl - Large   (60 pages, ~12 min)"
    echo " 4) Save graph to database (Neo4j import)"
    echo " 5) Production stack (Neo4j + RAG + Interface)"
    echo " 6) Database only   (Neo4j)"
    echo " 7) Stop all containers"
    echo " 8) Restart production"
    echo " 0) Exit"
    echo "================================================="
    echo -n "Enter choice [0-8]: "
    read -n 1 choice
    echo
}

run_crawler() {
    local max_pages=$1
    echo "Starting crawler with MAX_PAGES=${max_pages}..."
    MAX_PAGES=$max_pages docker compose --profile scrape up --build
    echo ""
    echo "Crawl complete. Output: crawler/output/graph.json"
    echo "Run option 4 to import the graph into Neo4j."
}

while true; do
    show_menu

    if [ "$choice" == "1" ]; then
        run_crawler 10

    elif [ "$choice" == "2" ]; then
        run_crawler 30

    elif [ "$choice" == "3" ]; then
        run_crawler 60

    elif [ "$choice" == "4" ]; then
        echo "Importing graph into Neo4j..."
        echo "Starting Neo4j..."
        docker compose --profile production up -d neo4j
        echo "Waiting for Neo4j to be ready..."
        until docker compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1;" > /dev/null 2>&1; do
            echo "  Neo4j not ready yet, retrying in 3s..."
            sleep 3
        done
        echo "Neo4j is ready."
        echo "Running schema init + graph import..."
        docker compose --profile import run --rm --build \
            -e NEO4J_URI=bolt://neo4j:7687 \
            graph-import sh -c "node scripts/initSchema.js && node scripts/importGraph.js"
        echo ""
        echo "Import complete."
        echo "Neo4j browser: http://localhost:7474"

    elif [ "$choice" == "5" ]; then
        echo "Starting Production Profile..."
        docker compose --profile production up --build -d
        echo "Production services are spinning up in the background."
        echo ""
        echo "Neo4j:     http://localhost:7474"
        echo "RAG API:   http://localhost:8000"
        echo "Interface: http://localhost:3000"
        echo "Ollama:    http://localhost:11434  (local)"

    elif [ "$choice" == "6" ]; then
        echo "Starting Neo4j..."
        docker compose --profile production up -d neo4j
        echo ""
        echo "Neo4j browser: http://localhost:7474"
        echo "Bolt:          bolt://localhost:7687  (neo4j/password)"

    elif [ "$choice" == "7" ]; then
        echo "Stopping all containers..."
        docker compose --profile production --profile scrape --profile import down
        echo "All containers stopped."

    elif [ "$choice" == "8" ]; then
        echo "Restarting production..."
        docker compose --profile production down
        docker compose --profile production up --build -d
        echo ""
        echo "Neo4j:     http://localhost:7474"
        echo "RAG API:   http://localhost:8000"
        echo "Interface: http://localhost:3000"

    elif [ "$choice" == "0" ]; then
        echo "Goodbye."
        exit 0

    else
        echo "Invalid choice."
    fi

    echo ""
    echo "Press any key to return to menu..."
    read -n 1
    echo
done
