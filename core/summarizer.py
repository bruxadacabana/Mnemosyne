"""
Geração de resumo geral dos documentos indexados.
"""
from __future__ import annotations

import re
from typing import Any

from langchain_ollama import OllamaLLM

from .config import AppConfig
from .errors import SummarizationError


def _strip_think(text: str) -> str:
    """Remove blocos <think>...</think> gerados pelo Qwen3."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def summarize_all(vectorstore: Any, config: AppConfig) -> str:
    """
    Gera resumo dos temas principais da coleção indexada.

    Raises:
        SummarizationError: se a busca ou geração falhar.
    """
    try:
        docs = vectorstore.similarity_search(
            "tema principal assunto conteúdo resumo", k=8
        )
    except Exception as exc:
        raise SummarizationError(f"Falha ao buscar trechos: {exc}") from exc

    if not docs:
        return "Nenhum documento indexado para resumir."

    context = "\n\n---\n".join(doc.page_content for doc in docs)

    prompt = (
        "Analise os trechos abaixo e forneça um resumo conciso "
        "dos principais temas e conteúdos encontrados na coleção de documentos. "
        "Responda em português.\n\n"
        f"Trechos:\n{context}\n\n"
        "Resumo:"
    )

    try:
        llm = OllamaLLM(model=config.llm_model, temperature=0.2)
        return _strip_think(llm.invoke(prompt))
    except Exception as exc:
        raise SummarizationError(f"Falha ao gerar resumo: {exc}") from exc
