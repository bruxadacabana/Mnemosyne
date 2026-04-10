"""
Carregadores de documentos para diferentes formatos.
Suporta: PDF, DOCX, TXT, MD.
"""
from __future__ import annotations

import os

from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)

from .errors import DocumentLoadError, UnsupportedFormatError


_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def load_documents(
    directory: str,
) -> tuple[list[Document], list[DocumentLoadError]]:
    """
    Carrega todos os documentos suportados de um diretório (recursivo).

    Retorna tupla (documentos_carregados, erros_por_arquivo).
    Nunca falha por causa de um único arquivo — erros são acumulados e
    retornados para que a camada superior decida o que fazer.

    Raises:
        FileNotFoundError: se o diretório não existir.
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Diretório não encontrado: {directory}")

    documents: list[Document] = []
    errors: list[DocumentLoadError] = []

    for root, _, files in os.walk(directory):
        # Ignorar diretório .mnemosyne (dados internos do app)
        if ".mnemosyne" in root.split(os.sep):
            continue
        for filename in sorted(files):
            _, ext = os.path.splitext(filename.lower())
            if ext not in _SUPPORTED_EXTENSIONS:
                continue
            file_path = os.path.join(root, filename)
            try:
                documents.extend(_load_file(file_path))
            except DocumentLoadError as exc:
                errors.append(exc)

    return documents, errors


def load_single_file(file_path: str) -> list[Document]:
    """
    Carrega um único arquivo.

    Raises:
        FileNotFoundError: se o arquivo não existir.
        UnsupportedFormatError: se o formato não for suportado.
        DocumentLoadError: se a leitura falhar.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    return _load_file(file_path)


def _load_file(file_path: str) -> list[Document]:
    """
    Despacha para o loader correto e converte exceções em DocumentLoadError.

    Raises:
        UnsupportedFormatError: se a extensão não for suportada.
        DocumentLoadError: em qualquer falha de leitura.
    """
    _, ext = os.path.splitext(file_path.lower())

    try:
        if ext == ".pdf":
            return PyPDFLoader(file_path).load()
        elif ext == ".docx":
            return Docx2txtLoader(file_path).load()
        elif ext in (".txt", ".md"):
            return TextLoader(file_path, encoding="utf-8").load()
        else:
            raise UnsupportedFormatError(file_path)
    except (DocumentLoadError, UnsupportedFormatError):
        raise
    except OSError as exc:
        raise DocumentLoadError(file_path, str(exc)) from exc
    except Exception as exc:
        raise DocumentLoadError(file_path, str(exc)) from exc
