from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class Document:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str
    index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestStats:
    doc_count: int = 0
    chunk_count: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    answer: str
    source_chunks: list[Chunk]
    latency_ms: float
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PipelineAdapter(Protocol):
    async def ingest(self, docs: list[Document]) -> IngestStats: ...
    async def query(self, question: str, top_k: int = 5) -> PipelineResult: ...
    async def teardown(self) -> None: ...
