import os
import tempfile
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chain import QueryChain
from graph_client import GraphClient
from vector_store import VectorStore

load_dotenv()

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

_vector_store: Optional[VectorStore] = None
_graph_client: Optional[GraphClient] = None
_query_chain: Optional[QueryChain] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _vector_store, _graph_client, _query_chain

    _vector_store = VectorStore()
    _graph_client = GraphClient()
    _query_chain = QueryChain(_vector_store, _graph_client)

    yield

    if _graph_client is not None:
        _graph_client.close()


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="IMDB Helper RAG Service",
    description="RAG + LLM Brain service for the IMDB Helper project.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    steps: list[dict[str, Any]]
    start_node_id: str
    end_node_id: str


class IngestResponse(BaseModel):
    status: str
    filename: str
    chunks_ingested: str


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness check."""
    return HealthResponse(status="ok")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Accept a natural-language question and return a step-by-step navigation answer."""
    if _query_chain is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty")

    result: dict[str, Any] = _query_chain.run(request.question)

    return QueryResponse(
        answer=result.get("answer", ""),
        steps=result.get("steps", []),
        start_node_id=result.get("start_node_id", ""),
        end_node_id=result.get("end_node_id", ""),
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
    """Accept a text/markdown/PDF file upload and ingest it into the vector store."""
    if _vector_store is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    allowed_content_types = {
        "text/plain",
        "text/markdown",
        "application/pdf",
        "application/octet-stream",
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_content_types and not content_type.startswith("text/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {content_type}. Use text, markdown, or PDF.",
        )

    filename: str = file.filename or "uploaded_file"

    file_bytes: bytes = await file.read()

    suffix = os.path.splitext(filename)[1] or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path: str = tmp.name

    try:
        _vector_store.ingest_file(tmp_path, filename)
    finally:
        os.unlink(tmp_path)

    return IngestResponse(
        status="ok",
        filename=filename,
        chunks_ingested="ingested",
    )
