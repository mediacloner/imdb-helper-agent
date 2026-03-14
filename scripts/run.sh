#!/bin/bash

echo "================================================="
echo " Autonomous Web UI Agent - Docker Runner"
echo "================================================="
echo "Select which profile to run:"
echo "  1) Scrape (Crawler phase)"
echo "  2) Production (Neo4j, RAG, React Interface)"
echo "================================================="
echo -n "Enter 1 or 2: "
read choice

if [ "$choice" == "1" ]; then
    echo "Starting Scrape Profile..."
    docker compose --profile scrape up --build
elif [ "$choice" == "2" ]; then
    echo "Starting Production Profile..."
    docker compose --profile production up --build -d
    echo "Production services are spinning up in the background."
    echo "Pulling local models into Ollama (this may take a few minutes on first run)..."
    docker compose exec ollama ollama pull qwen3:8b
    docker compose exec ollama ollama pull nomic-embed-text
    echo "Neo4j:     http://localhost:7474"
    echo "RAG API:   http://localhost:8000"
    echo "Interface: http://localhost:3000"
    echo "Ollama:    http://localhost:11434"
else
    echo "Invalid choice. Exiting."
    exit 1
fi
