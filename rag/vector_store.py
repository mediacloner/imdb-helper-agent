import os
from typing import Any

import chromadb
from chromadb import Collection
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings


class VectorStore:
    def __init__(self) -> None:
        self._embedder = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
        )
        self._client = chromadb.PersistentClient(path="./chroma_data")
        self._collection: Collection = self._client.get_or_create_collection(
            name="manuals",
            metadata={"hnsw:space": "cosine"},
        )
        # Primary splitter: split on markdown headers so each section stays together
        self._header_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=80,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "],
            length_function=len,
        )
        # Fallback splitter for very long sections
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=60,
            length_function=len,
        )

    def ingest_text(self, text: str, metadata: dict[str, Any]) -> None:
        """Split text into chunks and add them to the ChromaDB collection."""
        chunks: list[str] = self._header_splitter.split_text(text)
        if not chunks:
            return

        embeddings: list[list[float]] = self._embedder.embed_documents(chunks)

        ids: list[str] = [
            f"{metadata.get('filename', 'doc')}_{i}" for i in range(len(chunks))
        ]
        metadatas: list[dict[str, Any]] = [
            {**metadata, "chunk_index": i} for i in range(len(chunks))
        ]

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

    def ingest_file(self, file_path: str, filename: str) -> None:
        """Read a file from disk and ingest its text content."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        self.ingest_text(text, metadata={"filename": filename, "source": file_path})

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Return the top-k most relevant chunks for a query."""
        query_embedding: list[float] = self._embedder.embed_query(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[dict[str, Any]] = []
        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]
        distances = results.get("distances") or [[]]

        for doc, meta, dist in zip(documents[0], metadatas[0], distances[0]):
            chunks.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "score": 1.0 - dist,
                }
            )
        return chunks
