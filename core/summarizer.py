"""
Geração de resumo geral dos documentos indexados.
"""
from __future__ import annotations

from typing import Any

from langchain_ollama import OllamaLLM

from .config import AppConfig
from .errors import SummarizationError
from .rag import strip_think


def prepare_summary(vectorstore: Any, config: AppConfig) -> str:
    """
    Recupera trechos relevantes e retorna o prompt de sumarização.
    Usado pelo worker para streaming com possibilidade de interrupção.

    Raises:
        SummarizationError: se a busca vetorial falhar ou não houver docs.
    """
    try:
        docs = vectorstore.similarity_search(
            "tema principal assunto conteúdo resumo", k=4
        )
    except Exception as exc:
        raise SummarizationError(f"Falha ao buscar trechos: {exc}") from exc

    if not docs:
        raise SummarizationError("Nenhum documento indexado para resumir.")

    context_parts = []
    total_chars = 0
    for doc in docs:
        chunk = doc.page_content[:600]
        total_chars += len(chunk)
        if total_chars > 2400:
            break
        context_parts.append(chunk)

    context = "\n\n---\n".join(context_parts)

    return (
        "Analise os trechos abaixo e forneça um resumo conciso "
        "dos principais temas e conteúdos encontrados na coleção de documentos. "
        "Responda em português.\n\n"
        f"Trechos:\n{context}\n\n"
        "Resumo:"
    )


def summarize_all(vectorstore: Any, config: AppConfig) -> str:
    """
    Sumarização síncrona (sem streaming). Mantida para compatibilidade.

    Raises:
        SummarizationError: se a busca ou geração falhar.
    """
    try:
        prompt = prepare_summary(vectorstore, config)
        llm = OllamaLLM(model=config.llm_model, temperature=0.2, timeout=120)
        return strip_think(llm.invoke(prompt))
    except SummarizationError:
        raise
    except Exception as exc:
        raise SummarizationError(f"Falha ao gerar resumo: {exc}") from exc
