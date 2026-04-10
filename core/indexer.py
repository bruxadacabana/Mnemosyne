"""
Indexing e vectorstore: divide documentos em chunks e persiste com Chroma.
"""
from __future__ import annotations

import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from .config import AppConfig
from .errors import EmptyDirectoryError, IndexBuildError, VectorstoreNotFoundError
from .loaders import load_documents, load_single_file


def _get_splitter(config: AppConfig) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )


def _get_embeddings(config: AppConfig) -> OllamaEmbeddings:
    return OllamaEmbeddings(model=config.embed_model)


def create_vectorstore(config: AppConfig) -> Chroma:
    """
    Carrega documentos de config.watched_dir (e opcionalmente config.vault_dir),
    divide em chunks e cria vectorstore único com metadata source_type.

    Raises:
        FileNotFoundError: se o diretório não existir.
        EmptyDirectoryError: se nenhum documento for encontrado.
        IndexBuildError: se a criação do Chroma falhar.
    """
    documents, _ = load_documents(config.watched_dir, source_type="biblioteca")

    # Indexar vault do Obsidian se configurado
    if config.vault_dir and os.path.isdir(config.vault_dir):
        vault_docs, _ = load_documents(config.vault_dir, source_type="vault")
        documents.extend(vault_docs)

    if not documents:
        raise EmptyDirectoryError(config.watched_dir)

    splitter = _get_splitter(config)
    chunks = splitter.split_documents(documents)

    try:
        os.makedirs(config.persist_dir, exist_ok=True)
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=_get_embeddings(config),
            persist_directory=config.persist_dir,
        )
    except Exception as exc:
        raise IndexBuildError(f"Falha ao criar vectorstore: {exc}") from exc

    return vectorstore


def index_single_file(file_path: str, config: AppConfig) -> Chroma:
    """
    Indexa um único arquivo e adiciona ao vectorstore existente (ou cria novo).
    Usado pelo watcher para indexação incremental sem rebuild completo.

    Raises:
        DocumentLoadError: se o arquivo não puder ser carregado.
        IndexBuildError: se a atualização do Chroma falhar.
    """
    docs = load_single_file(file_path)
    if not docs:
        return load_vectorstore(config)

    splitter = _get_splitter(config)
    chunks = splitter.split_documents(docs)

    try:
        os.makedirs(config.persist_dir, exist_ok=True)
        vs = Chroma(
            persist_directory=config.persist_dir,
            embedding_function=_get_embeddings(config),
        )
        vs.add_documents(chunks)
    except Exception as exc:
        raise IndexBuildError(f"Falha ao adicionar ao vectorstore: {exc}") from exc

    return vs


def load_vectorstore(config: AppConfig) -> Chroma:
    """
    Carrega um vectorstore já persistido.

    Raises:
        VectorstoreNotFoundError: se o persist_dir não existir.
    """
    if not config.persist_dir or not os.path.exists(config.persist_dir):
        raise VectorstoreNotFoundError(config.persist_dir)

    return Chroma(
        persist_directory=config.persist_dir,
        embedding_function=_get_embeddings(config),
    )
