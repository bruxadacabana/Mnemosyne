"""
Gerenciamento de contexto pessoal — SessionMemory e CollectionIndex.

SessionMemory: histórico de queries da sessão atual (não persiste por padrão).
CollectionIndex: índice leve de coleções indexadas (persiste em .mnemosyne/index.json).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


# ── SessionMemory ─────────────────────────────────────────────────────────────


@dataclass
class QueryRecord:
    question: str
    answer: str
    sources: list[str]
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class SessionMemory:
    """
    Histórico de queries da sessão atual.
    Não persiste entre sessões — vive apenas na memória do processo.
    """

    def __init__(self, max_size: int = 50) -> None:
        self._records: list[QueryRecord] = []
        self._max_size = max_size

    def save_query(
        self, question: str, answer: str, sources: list[str]
    ) -> None:
        self._records.append(QueryRecord(question=question, answer=answer, sources=sources))
        if len(self._records) > self._max_size:
            self._records.pop(0)

    def find_similar(self, question: str, min_overlap: int = 2) -> QueryRecord | None:
        """
        Busca a query mais recente com sobreposição mínima de tokens.
        Retorna None se nenhuma satisfizer o critério.
        """
        tokens = set(question.lower().split())
        best: QueryRecord | None = None
        best_score = 0
        for record in reversed(self._records):
            rec_tokens = set(record.question.lower().split())
            overlap = len(tokens & rec_tokens)
            if overlap >= min_overlap and overlap > best_score:
                best = record
                best_score = overlap
        return best

    @property
    def records(self) -> list[QueryRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()


# ── CollectionIndex ───────────────────────────────────────────────────────────


@dataclass
class CollectionInfo:
    name: str
    path: str
    total_files: int = 0
    last_indexed: str = ""
    file_types: dict[str, int] = field(default_factory=dict)
    summary: str = ""


class CollectionIndex:
    """
    Índice leve de coleções indexadas.
    Persiste em <mnemosyne_dir>/index.json.
    """

    def __init__(self, mnemosyne_dir: str) -> None:
        self._path = Path(mnemosyne_dir) / "index.json"
        self._collections: list[CollectionInfo] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open(encoding="utf-8") as f:
                data = json.load(f)
            self._collections = [CollectionInfo(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._collections = []

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(
                [asdict(c) for c in self._collections],
                f,
                indent=2,
                ensure_ascii=False,
            )

    def update(self, info: CollectionInfo) -> None:
        for i, c in enumerate(self._collections):
            if c.path == info.path:
                self._collections[i] = info
                self.save()
                return
        self._collections.append(info)
        self.save()

    def get(self, path: str) -> CollectionInfo | None:
        return next((c for c in self._collections if c.path == path), None)

    @property
    def collections(self) -> list[CollectionInfo]:
        return list(self._collections)
