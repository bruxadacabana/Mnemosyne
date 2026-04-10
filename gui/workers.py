# Threads para indexação, consultas e resumos.
from __future__ import annotations

from langchain_ollama import OllamaLLM
from PySide6.QtCore import QThread, Signal

from core.config import AppConfig
from core.errors import (
    MnemosyneError,
    OllamaUnavailableError,
    ModelNotFoundError,
    DocumentLoadError,
    IndexBuildError,
    EmptyDirectoryError,
    QueryError,
    SummarizationError,
)
from core.indexer import create_vectorstore, index_single_file
from core.memory import Turn
from core.ollama_client import list_models, validate_model
from core.rag import prepare_ask, strip_think, AskResult
from core.summarizer import prepare_summary


class OllamaCheckWorker(QThread):
    """Verifica disponibilidade do Ollama e lista modelos instalados."""

    models_loaded = Signal(list)      # list[OllamaModel]
    ollama_unavailable = Signal(str)  # mensagem de erro

    def run(self) -> None:
        try:
            models = list_models()
            self.models_loaded.emit(models)
        except OllamaUnavailableError as exc:
            self.ollama_unavailable.emit(str(exc))
        except Exception as exc:
            self.ollama_unavailable.emit(f"Erro inesperado ao contatar Ollama: {exc}")


class IndexWorker(QThread):
    """Indexa todos os documentos da pasta monitorada."""

    finished = Signal(bool, str)  # sucesso, mensagem

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:
        try:
            create_vectorstore(self.config)
            self.finished.emit(True, "Indexação concluída com sucesso.")
        except EmptyDirectoryError as exc:
            self.finished.emit(False, str(exc))
        except IndexBuildError as exc:
            self.finished.emit(False, f"Erro na indexação: {exc}")
        except FileNotFoundError as exc:
            self.finished.emit(False, f"Pasta não encontrada: {exc}")
        except MnemosyneError as exc:
            self.finished.emit(False, str(exc))


class IndexFileWorker(QThread):
    """Indexa um único arquivo — usado pelo watcher de pasta."""

    finished = Signal(bool, str)  # sucesso, mensagem

    def __init__(self, file_path: str, config: AppConfig) -> None:
        super().__init__()
        self.file_path = file_path
        self.config = config

    def run(self) -> None:
        import os

        try:
            index_single_file(self.file_path, self.config)
            name = os.path.basename(self.file_path)
            self.finished.emit(True, f"'{name}' indexado.")
        except DocumentLoadError as exc:
            self.finished.emit(False, f"Erro ao carregar arquivo: {exc}")
        except IndexBuildError as exc:
            self.finished.emit(False, f"Erro na indexação: {exc}")
        except MnemosyneError as exc:
            self.finished.emit(False, str(exc))


class AskWorker(QThread):
    """Executa uma consulta RAG com streaming token a token."""

    token = Signal(str)                       # token recebido durante streaming
    finished = Signal(bool, str, list, list)  # sucesso, resposta/erro, fontes, turns_updated

    def __init__(
        self,
        vectorstore,
        question: str,
        config: AppConfig,
        chat_history: list[Turn] | None = None,
    ) -> None:
        super().__init__()
        self.vectorstore = vectorstore
        self.question = question
        self.config = config
        self.chat_history: list[Turn] = list(chat_history) if chat_history else []

    def run(self) -> None:
        try:
            prompt, sources = prepare_ask(
                self.vectorstore, self.question, self.config, self.chat_history
            )
        except QueryError as exc:
            self.finished.emit(False, str(exc), [], self.chat_history)
            return
        except Exception as exc:
            self.finished.emit(False, f"Erro na recuperação: {exc}", [], self.chat_history)
            return

        try:
            validate_model(self.config.llm_model)
        except ModelNotFoundError as exc:
            self.finished.emit(False, str(exc), [], self.chat_history)
            return
        except OllamaUnavailableError as exc:
            self.finished.emit(False, str(exc), [], self.chat_history)
            return

        try:
            llm = OllamaLLM(model=self.config.llm_model, temperature=0)
            full = ""
            for chunk in llm.stream(prompt):
                if self.isInterruptionRequested():
                    self.finished.emit(False, "Interrompido.", [], self.chat_history)
                    return
                self.token.emit(chunk)
                full += chunk
            answer = strip_think(full)
            updated = list(self.chat_history) + [
                Turn(role="user", content=self.question),
                Turn(role="assistant", content=answer, sources=sources),
            ]
            self.finished.emit(True, answer, sources, updated)
        except Exception as exc:
            self.finished.emit(False, f"Erro na consulta: {exc}", [], self.chat_history)


class SummarizeWorker(QThread):
    """Gera resumo geral da coleção indexada com streaming."""

    token = Signal(str)       # token recebido durante streaming
    finished = Signal(bool, str)  # sucesso, resumo/erro

    def __init__(self, vectorstore, config: AppConfig) -> None:
        super().__init__()
        self.vectorstore = vectorstore
        self.config = config

    def run(self) -> None:
        try:
            prompt = prepare_summary(self.vectorstore, self.config)
        except SummarizationError as exc:
            self.finished.emit(False, str(exc))
            return
        except Exception as exc:
            self.finished.emit(False, f"Erro ao preparar resumo: {exc}")
            return

        try:
            validate_model(self.config.llm_model)
        except ModelNotFoundError as exc:
            self.finished.emit(False, str(exc))
            return
        except OllamaUnavailableError as exc:
            self.finished.emit(False, str(exc))
            return

        try:
            llm = OllamaLLM(model=self.config.llm_model, temperature=0.2, timeout=120)
            full = ""
            for chunk in llm.stream(prompt):
                if self.isInterruptionRequested():
                    self.finished.emit(False, "Interrompido.")
                    return
                self.token.emit(chunk)
                full += chunk
            self.finished.emit(True, strip_think(full))
        except SummarizationError as exc:
            self.finished.emit(False, str(exc))
        except Exception as exc:
            self.finished.emit(False, f"Erro inesperado: {exc}")
