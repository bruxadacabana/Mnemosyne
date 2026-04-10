"""
QA: recupera chunks relevantes e gera resposta via Ollama.
"""
from __future__ import annotations

import re
from typing import Any, TypedDict

from langchain_ollama import OllamaLLM

from .config import AppConfig
from .errors import QueryError


class AskResult(TypedDict):
    answer: str
    sources: list[str]


_PROMPT_TEMPLATE = (
    "Você é Mnemosyne, um bibliotecário celeste que ajuda a encontrar informações "
    "em documentos pessoais.\n"
    "Use apenas os trechos fornecidos abaixo para responder. "
    "Se a informação não estiver nos trechos, diga que não encontrou nos documentos indexados. "
    "Responda em português.\n\n"
    "Trechos relevantes:\n{context}\n\n"
    "Pergunta: {question}\n\n"
    "Resposta:"
)


def strip_think(text: str) -> str:
    """Remove blocos <think>...</think> gerados pelo Qwen3."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def prepare_ask(
    vectorstore: Any, question: str, config: AppConfig
) -> tuple[str, list[str]]:
    """
    Recupera documentos relevantes e retorna (prompt, sources).
    Usado pelo worker para streaming com possibilidade de interrupção.

    Raises:
        QueryError: se a busca vetorial falhar.
    """
    try:
        docs = vectorstore.similarity_search(question, k=config.retriever_k)
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

    prompt = _PROMPT_TEMPLATE.format(context=context, question=question)
    return prompt, sources


def ask(vectorstore: Any, question: str, config: AppConfig) -> AskResult:
    """
    Consulta RAG síncrona (sem streaming).

    Raises:
        QueryError: se a chain falhar por qualquer motivo.
    """
    try:
        prompt, sources = prepare_ask(vectorstore, question, config)
        llm = OllamaLLM(model=config.llm_model, temperature=0)
        answer = strip_think(llm.invoke(prompt))
    except QueryError:
        raise
    except Exception as exc:
        raise QueryError(f"Falha na consulta: {exc}") from exc

    return AskResult(answer=answer, sources=sources)
