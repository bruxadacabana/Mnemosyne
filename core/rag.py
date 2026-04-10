"""
QA chain: recupera chunks relevantes e gera resposta via Ollama.
"""
from __future__ import annotations

import os
import re
from typing import Any, TypedDict

from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from .config import AppConfig
from .errors import QueryError


class AskResult(TypedDict):
    answer: str
    sources: list[str]  # paths absolutos das fontes, sem duplicatas


_PROMPT = PromptTemplate(
    template=(
        "Você é Mnemosyne, um bibliotecário celeste que ajuda a encontrar informações "
        "em documentos pessoais.\n"
        "Use apenas os trechos fornecidos abaixo para responder. "
        "Se a informação não estiver nos trechos, diga que não encontrou nos documentos indexados. "
        "Responda em português.\n\n"
        "Trechos relevantes:\n{context}\n\n"
        "Pergunta: {question}\n\n"
        "Resposta:"
    ),
    input_variables=["context", "question"],
)


def _strip_think(text: str) -> str:
    """Remove blocos <think>...</think> gerados pelo Qwen3."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def setup_qa_chain(vectorstore: Any, config: AppConfig) -> RetrievalQA:
    llm = OllamaLLM(model=config.llm_model, temperature=0)
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": config.retriever_k}),
        chain_type_kwargs={"prompt": _PROMPT},
        return_source_documents=True,
    )
    return chain


def ask(vectorstore: Any, question: str, config: AppConfig) -> AskResult:
    """
    Executa a consulta RAG e retorna resposta estruturada com fontes.

    Raises:
        QueryError: se a chain falhar por qualquer motivo.
    """
    try:
        chain = setup_qa_chain(vectorstore, config)
        result = chain.invoke({"query": question})
    except Exception as exc:
        raise QueryError(f"Falha na consulta: {exc}") from exc

    answer = _strip_think(result["result"])

    seen: set[str] = set()
    sources: list[str] = []
    for doc in result.get("source_documents", []):
        src = doc.metadata.get("source", "")
        if src and src not in seen:
            seen.add(src)
            sources.append(src)

    return AskResult(answer=answer, sources=sources)
