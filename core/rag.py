"""
QA: recupera chunks relevantes e gera resposta via Ollama.
"""
from __future__ import annotations

import re
from typing import Any, TypedDict

from langchain_core.documents import Document
from langchain_ollama import OllamaLLM
from rank_bm25 import BM25Okapi

from .config import AppConfig
from .errors import QueryError
from .memory import Turn


class AskResult(TypedDict):
    answer: str
    sources: list[str]


_SYSTEM_PROMPT = (
    "Você é Mnemosyne, um bibliotecário celeste que ajuda a encontrar informações "
    "em documentos pessoais.\n"
    "Use apenas os trechos fornecidos abaixo para responder. "
    "Se a informação não estiver nos trechos, diga que não encontrou nos documentos indexados. "
    "Responda em português."
)

_PROMPT_TEMPLATE = (
    "{system}\n\n"
    "{history}"
    "Trechos relevantes:\n{context}\n\n"
    "Pergunta: {question}\n\n"
    "Resposta:"
)

# Cap do histórico injectado no prompt (caracteres)
_HISTORY_CAP = 6_000
# Quantos turnos recentes incluir
_HISTORY_TURNS = 5


def strip_think(text: str) -> str:
    """Remove blocos <think>...</think> gerados pelo Qwen3."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _hybrid_retrieve(
    vectorstore: Any,
    question: str,
    k: int,
    source_type: str | None = None,
) -> list[Document]:
    """
    Hybrid retrieval: combina busca semântica e BM25.
    Retorna até k documentos únicos, ordenados por score combinado.
    """
    # Semântico: buscar k*2 candidatos para ter mais para o BM25 filtrar
    search_kwargs: dict = {"k": k * 2}
    if source_type:
        search_kwargs["filter"] = {"source_type": source_type}
    try:
        semantic_docs = vectorstore.similarity_search(question, **search_kwargs)
    except Exception as exc:
        raise QueryError(f"Falha na recuperação semântica: {exc}") from exc

    if not semantic_docs:
        return []

    # BM25 sobre o pool semântico
    tokenized_corpus = [doc.page_content.lower().split() for doc in semantic_docs]
    tokenized_query = question.lower().split()

    try:
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(tokenized_query)
    except Exception:
        # Se BM25 falhar, retornar só o resultado semântico
        return semantic_docs[:k]

    # Normalizar BM25 para [0, 1]
    max_score = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    normalized = [s / max_score for s in bm25_scores]

    # Score combinado: 0.6 semântico (posição inversa) + 0.4 BM25
    n = len(semantic_docs)
    combined = [
        (0.6 * (1.0 - i / n) + 0.4 * normalized[i], i)
        for i in range(n)
    ]
    combined.sort(key=lambda x: x[0], reverse=True)

    # Deduplicar por conteúdo, limitar a k
    seen: set[str] = set()
    results: list[Document] = []
    for _, idx in combined:
        doc = semantic_docs[idx]
        key = doc.page_content[:200]
        if key not in seen:
            seen.add(key)
            results.append(doc)
        if len(results) >= k:
            break

    return results


def _format_history(turns: list[Turn]) -> str:
    """Formata os últimos turnos como texto para o prompt, respeitando o cap."""
    recent = turns[-_HISTORY_TURNS:]
    lines: list[str] = []
    total = 0
    for turn in reversed(recent):
        prefix = "Utilizador" if turn.role == "user" else "Mnemosyne"
        entry = f"{prefix}: {turn.content}"
        if total + len(entry) > _HISTORY_CAP:
            break
        lines.insert(0, entry)
        total += len(entry)
    if not lines:
        return ""
    return "[Histórico da conversa]\n" + "\n".join(lines) + "\n\n"


def prepare_ask(
    vectorstore: Any,
    question: str,
    config: AppConfig,
    chat_history: list[Turn] | None = None,
    source_type: str | None = None,
) -> tuple[str, list[str]]:
    """
    Recupera documentos relevantes e retorna (prompt, sources).
    Usado pelo worker para streaming com possibilidade de interrupção.

    chat_history: turnos anteriores da sessão para contexto multi-turno.
    source_type: filtrar por "biblioteca", "vault" ou None (ambos).

    Raises:
        QueryError: se a busca vetorial falhar.
    """
    try:
        docs = _hybrid_retrieve(vectorstore, question, config.retriever_k, source_type)
    except QueryError:
        raise
    except Exception as exc:
        raise QueryError(f"Falha na recuperação: {exc}") from exc

    context = "\n\n---\n".join(doc.page_content for doc in docs)

    seen: set[str] = set()
    sources: list[str] = []
    for doc in docs:
        src = doc.metadata.get("source", "")
        if src and src not in seen:
            seen.add(src)
            sources.append(src)

    history_text = _format_history(chat_history) if chat_history else ""
    prompt = _PROMPT_TEMPLATE.format(
        system=_SYSTEM_PROMPT,
        history=history_text,
        context=context,
        question=question,
    )
    return prompt, sources


def ask(
    vectorstore: Any,
    question: str,
    config: AppConfig,
    chat_history: list[Turn] | None = None,
    source_type: str | None = None,
) -> AskResult:
    """
    Consulta RAG síncrona (sem streaming).

    Raises:
        QueryError: se a chain falhar por qualquer motivo.
    """
    try:
        prompt, sources = prepare_ask(vectorstore, question, config, chat_history, source_type)
        llm = OllamaLLM(model=config.llm_model, temperature=0)
        answer = strip_think(llm.invoke(prompt))
    except QueryError:
        raise
    except Exception as exc:
        raise QueryError(f"Falha na consulta: {exc}") from exc

    return AskResult(answer=answer, sources=sources)
